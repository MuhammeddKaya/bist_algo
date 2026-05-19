"""
BIST hisse evreni — hacme göre sıralı dinamik liste.

~200 bilinen BIST hissesini yfinance'tan batch indirir,
son 20 günlük ortalama TL hacmine göre sıralar ve top-N döner.

Kullanım:
    from data_feed.universe import get_universe
    symbols = get_universe(top_n=100)
"""

import os
import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# ~200 bilinen BIST hissesi (IPO / delist olmadıkça stabil)
BIST_EVREN_GENIS = [
    # Bankacılık
    "GARAN","AKBNK","ISCTR","YKBNK","HALKB","VAKBN","SKBNK","TSKB","ALBRK","QNBFB",
    # Holding / Finans
    "KCHOL","SISE","SAHOL","DOHOL","ENKAI","GLYHO","OYAKC","AGHOL",
    # Enerji / Petrokimya
    "TUPRS","PETKM","AKSEN","ZOREN","AKENR","ORGE","IPEKE","SASA","ENJSA","ODAS",
    # Demir-Çelik / Metal
    "EREGL","KRDMD","ISDMR","BRSAN","DMSAS","CEMAS","EMKEL",
    # Havacılık / Savunma / Ulaşım
    "THYAO","ASELS","PGSUS","TAVHL","HAVAS","ULAS","RYSAS",
    # Otomotiv
    "TOASO","FROTO","TTRAK","DOAS","OTKAR","BRISA","ASUZU",
    # Beyaz Eşya / Elektronik
    "ARCLK","VESTL","VESBE",
    # Perakende / Gıda / İçecek
    "BIMAS","MGROS","ULKER","CCOLA","AEFES","TATGD","SOKM","KENT","KNFRT",
    # Tekstil / Hazır Giyim
    "MAVI","KORDS","SKTAS","SUWEN","YUNSA",
    # Telekom
    "TCELL","TTKOM",
    # Teknoloji / Yazılım
    "LOGO","NETAS","INDES","KAREL","ARENA","LINK","TERA","PENTA","INTEM","TKNSA",
    "ACSEL","DGATE","OBASE","SMART","PAPIL",
    # Cam / Çimento / İnşaat Malz.
    "TRKCM","AKCNS","CIMSA","BOLUC","ADANA","BUCIM","KRSTL","KUTPO",
    # GYO
    "TRGYO","ISGYO","EKGYO","HLGYO","VKGYO","RYGYO","NUGYO","YGYO",
    # Kimya / Tarım
    "SODA","ALKIM","GUBRF","HEKTS","GESAN","KLKIM","IPMAN",
    # Madencilik
    "KOZAL","KOZAA",
    # Sigorta
    "ANSGR","AKGRT","RAYSG",
    # Sağlık / İlaç
    "DEVA","ECILC","SELEC","BFREN","MTRKS",
    # Spor
    "FENER","BJKAS","GSRAY","TSPOR",
    # Küçük / Diğer
    "ARDYZ","MANAS","BAHKM","PRKAB","KONTR","NTTUR",
    "YATAS","KRONT","CANTE","HATEK","FLAP","FORMT",
    "GEDZA","GENTS","GOODY","HRKET","JANTS","KATMR",
    "LKMNH","MAKIM","MARBL","MEPET","MERCN","NIBAS",
    "PENGD","POLHO","SAMAT","SEKFK","TACTR","TEKTU",
    "TGSAS","ULUUN","UNLU","USAK","VAKKO","VERUS",
]


def _batch_hacim(semboller: list[str]) -> dict[str, float]:
    """yfinance batch download ile tüm hisselerin 20g ortalama TL hacmini döner."""
    hacimler = {s: 0.0 for s in semboller}
    try:
        raw = yf.download(
            semboller, period="30d", interval="1d",
            progress=False, auto_adjust=True, group_by="ticker"
        )
    except Exception as e:
        logger.warning("Batch download hatası: %s", e)
        return hacimler

    for sym in semboller:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                if sym not in raw.columns.get_level_values(0):
                    continue
                df = raw[sym]
            else:
                df = raw
            df = df.dropna(subset=["Close", "Volume"])
            if df.empty:
                continue
            hacimler[sym] = float((df["Close"] * df["Volume"]).tail(20).mean()) / 1_000_000
        except Exception:
            pass
    return hacimler


def get_universe(top_n: int = 100, cache_saat: int = 12) -> list[str]:
    """
    En likit BIST hisselerini döner (.IS uzantılı, hacme göre sıralı).
    Sonuçları cache'ler — aynı gün içinde tekrar çağrılırsa cache kullanır.
    """
    cache_path = os.path.join("data", "universe_cache.txt")
    os.makedirs("data", exist_ok=True)

    # Cache kontrolü
    if os.path.exists(cache_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - mtime < timedelta(hours=cache_saat):
            with open(cache_path) as f:
                cached = [l.strip() for l in f if l.strip()]
            if cached:
                logger.info("Evren cache'ten yüklendi (%d hisse)", len(cached))
                return cached[:top_n]

    semboller = [f"{k}.IS" for k in BIST_EVREN_GENIS]
    print(f"  {len(semboller)} hisse için hacim hesaplanıyor (batch)...", end=" ", flush=True)
    hacimler = _batch_hacim(semboller)

    sirali = sorted(
        [(sym, h) for sym, h in hacimler.items() if h > 0],
        key=lambda x: x[1], reverse=True
    )
    print(f"tamamlandı — ilk 3: {[(s, f'{h:.0f}M') for s,h in sirali[:3]]}")

    sonuc = [sym for sym, _ in sirali[:top_n]]

    with open(cache_path, "w") as f:
        f.write("\n".join(sonuc))

    return sonuc


if __name__ == "__main__":
    sonuc = get_universe(top_n=100)
    print(f"\nEn likit {len(sonuc)} BIST hissesi:")
    for i, sym in enumerate(sonuc, 1):
        print(f"  {i:>3}. {sym}")
