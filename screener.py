"""
BIST ML Günlük Tarama — Her sabah piyasa açılmadan önce çalıştır.

3 ML modeli (SHAP-1g, SHAP-ATR, SHAP-5g) konsensüsüne göre hisseleri sıralar.
Göreli güç (BIST100'e karşı) ve likidite filtresi uygular.

Kullanım:
    python screener.py                    # varsayılan: min 5M TL hacim, tüm evren
    python screener.py --min-vol 10       # min 10M TL günlük hacim
    python screener.py --top 20           # en iyi 20 hisseyi göster
    python screener.py --min-consensus 3  # 3 modelin tamamı AL desin
"""

import argparse
import os
import sys
from datetime import datetime, date, timedelta

import pandas as pd
import yfinance as yf

# ── Hisse evreni (bist_model ile eğitilen 86 aktif hisse) ──────────────────
BIST_EVREN = [
    # Bankacılık
    "GARAN.IS", "AKBNK.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS",
    "VAKBN.IS", "SKBNK.IS", "TSKB.IS", "ALBRK.IS", "QNBFB.IS",
    # Holding
    "KCHOL.IS", "SISE.IS", "SAHOL.IS", "DOHOL.IS", "ENKAI.IS", "GLYHO.IS",
    # Enerji
    "TUPRS.IS", "PETKM.IS", "AKSEN.IS", "ZOREN.IS", "AKENR.IS",
    "ORGE.IS", "IPEKE.IS",
    # Demir-Çelik
    "EREGL.IS", "KRDMD.IS", "ISDMR.IS",
    # Havacılık-Savunma
    "THYAO.IS", "ASELS.IS", "PGSUS.IS", "TAVHL.IS",
    # Otomotiv
    "TOASO.IS", "FROTO.IS", "TTRAK.IS", "DOAS.IS", "OTKAR.IS", "BRISA.IS",
    # Beyaz Eşya-Elektronik
    "ARCLK.IS", "VESTL.IS", "VESBE.IS",
    # Perakende-Gıda
    "BIMAS.IS", "MGROS.IS", "ULKER.IS", "CCOLA.IS", "AEFES.IS", "TATGD.IS",
    # Tekstil
    "MAVI.IS", "KORDS.IS",
    # Telekom
    "TCELL.IS", "TTKOM.IS",
    # Teknoloji
    "LOGO.IS", "NETAS.IS", "INDES.IS", "KAREL.IS", "ARENA.IS", "LINK.IS",
    # Cam-Çimento
    "TRKCM.IS", "AKCNS.IS", "CIMSA.IS", "BOLUC.IS", "ADANA.IS",
    # GYO
    "TRGYO.IS", "ISGYO.IS", "EKGYO.IS", "HLGYO.IS", "VKGYO.IS",
    # Kimya-Tarım
    "SODA.IS", "ALKIM.IS", "GUBRF.IS", "HEKTS.IS", "GESAN.IS",
    # Madencilik
    "KOZAL.IS", "KOZAA.IS",
    # Sigorta
    "ANSGR.IS", "AKGRT.IS",
    # Sağlık-İlaç
    "DEVA.IS", "ECILC.IS", "SELEC.IS",
    # Spor
    "FENER.IS", "BJKAS.IS", "GSRAY.IS", "TSPOR.IS",
    # Diğer
    "ARDYZ.IS", "MANAS.IS", "BAHKM.IS", "BRSAN.IS", "PRKAB.IS",
    "KONTR.IS", "DMSAS.IS", "KLKIM.IS", "NTTUR.IS",
]

SEKTORLER = {
    "GARAN.IS": "Bankacılık",  "AKBNK.IS": "Bankacılık", "ISCTR.IS": "Bankacılık",
    "YKBNK.IS": "Bankacılık",  "HALKB.IS": "Bankacılık", "VAKBN.IS": "Bankacılık",
    "SKBNK.IS": "Bankacılık",  "TSKB.IS":  "Bankacılık", "ALBRK.IS": "Bankacılık",
    "QNBFB.IS": "Bankacılık",  "KCHOL.IS": "Holding",    "SISE.IS":  "Holding",
    "SAHOL.IS": "Holding",     "DOHOL.IS": "Holding",    "ENKAI.IS": "Holding",
    "GLYHO.IS": "Holding",     "TUPRS.IS": "Enerji",     "PETKM.IS": "Enerji",
    "AKSEN.IS": "Enerji",      "ZOREN.IS": "Enerji",     "AKENR.IS": "Enerji",
    "ORGE.IS":  "Enerji",      "IPEKE.IS": "Enerji",     "EREGL.IS": "Demir-Çelik",
    "KRDMD.IS": "Demir-Çelik", "ISDMR.IS": "Demir-Çelik","THYAO.IS": "Havacılık",
    "ASELS.IS": "Savunma",     "PGSUS.IS": "Havacılık",  "TAVHL.IS": "Havacılık",
    "TOASO.IS": "Otomotiv",    "FROTO.IS": "Otomotiv",   "TTRAK.IS": "Otomotiv",
    "DOAS.IS":  "Otomotiv",    "OTKAR.IS": "Otomotiv",   "BRISA.IS": "Otomotiv",
    "ARCLK.IS": "Beyaz Eşya",  "VESTL.IS": "Elektronik", "VESBE.IS": "Beyaz Eşya",
    "BIMAS.IS": "Perakende",   "MGROS.IS": "Perakende",  "ULKER.IS": "Gıda",
    "CCOLA.IS": "İçecek",      "AEFES.IS": "İçecek",     "TATGD.IS": "Gıda",
    "MAVI.IS":  "Tekstil",     "KORDS.IS": "Tekstil",    "TCELL.IS": "Telekom",
    "TTKOM.IS": "Telekom",     "LOGO.IS":  "Teknoloji",  "NETAS.IS": "Teknoloji",
    "INDES.IS": "Teknoloji",   "KAREL.IS": "Teknoloji",  "ARENA.IS": "Teknoloji",
    "LINK.IS":  "Teknoloji",   "TRKCM.IS": "Cam",        "AKCNS.IS": "Çimento",
    "CIMSA.IS": "Çimento",     "BOLUC.IS": "Çimento",    "ADANA.IS": "Çimento",
    "TRGYO.IS": "GYO",         "ISGYO.IS": "GYO",        "EKGYO.IS": "GYO",
    "HLGYO.IS": "GYO",         "VKGYO.IS": "GYO",        "SODA.IS":  "Kimya",
    "ALKIM.IS": "Kimya",       "GUBRF.IS": "Kimya",      "HEKTS.IS": "Tarım-Kim.",
    "GESAN.IS": "Elektrik",    "KOZAL.IS": "Madencilik", "KOZAA.IS": "Madencilik",
    "ANSGR.IS": "Sigorta",     "AKGRT.IS": "Sigorta",    "DEVA.IS":  "İlaç",
    "ECILC.IS": "İlaç",        "SELEC.IS": "İlaç",       "FENER.IS": "Spor",
    "BJKAS.IS": "Spor",        "GSRAY.IS": "Spor",       "TSPOR.IS": "Spor",
    "ARDYZ.IS": "Diğer",       "MANAS.IS": "Diğer",      "BAHKM.IS": "Sağlık",
    "BRSAN.IS": "Demir-Çelik", "PRKAB.IS": "Kablo",      "KONTR.IS": "İnşaat",
    "DMSAS.IS": "Metal",       "KLKIM.IS": "Kimya",      "NTTUR.IS": "Turizm",
}

CACHE_DIR = os.path.join("data", "market", "1d")


def _indir(sym: str, period: str = "2y") -> pd.DataFrame:
    try:
        df = yf.download(sym, period=period, interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df.dropna(subset=["Close", "Volume"])
    except Exception:
        return pd.DataFrame()


def veri_yukle(sym: str) -> pd.DataFrame:
    """Önce cache'ten yükle; bugün güncellenmemişse indir."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{sym}.csv")
    bugun = date.today()

    if os.path.exists(path):
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).date()
        if mtime >= bugun:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            return df.dropna(subset=["Close", "Volume"])

    df = _indir(sym, period="2y")
    if not df.empty:
        df.to_csv(path)
    return df


def goreli_guc(df: pd.DataFrame, bist_df: pd.DataFrame, gun: int = 20) -> float:
    """Hissenin son N günlük getirisini BIST100'ün getirisine böler. >1 = piyasayı geçiyor."""
    if len(df) < gun + 1 or len(bist_df) < gun + 1:
        return 0.0
    try:
        hisse_getiri = df["Close"].iloc[-1] / df["Close"].iloc[-gun] - 1
        bist_getiri  = bist_df["Close"].iloc[-1] / bist_df["Close"].iloc[-gun] - 1
        if abs(bist_getiri) < 0.001:
            return 1.0
        return round((1 + hisse_getiri) / (1 + bist_getiri), 2)
    except Exception:
        return 0.0


def ortalama_hacim_tl(df: pd.DataFrame, gun: int = 20) -> float:
    """Son N günlük ortalama TL hacmi (milyon)."""
    if len(df) < gun:
        return 0.0
    son = df.tail(gun)
    return round((son["Close"] * son["Volume"]).mean() / 1_000_000, 1)


def atr14(df: pd.DataFrame, period: int = 14) -> float:
    """14 günlük ATR değeri (TL cinsinden)."""
    if len(df) < period + 1:
        return 0.0
    try:
        h = df["High"]
        l = df["Low"]
        c = df["Close"]
        tr = pd.concat([
            h - l,
            (h - c.shift(1)).abs(),
            (l - c.shift(1)).abs(),
        ], axis=1).max(axis=1)
        return float(tr.tail(period).mean())
    except Exception:
        return 0.0


def tara(min_vol_m: float = 5.0, min_consensus: int = 1, top_n: int = 0,
         semboller: list = None) -> list[dict]:

    from ai_engine.ml_client import MLClient
    evren = semboller or BIST_EVREN

    print(f"\n  Modeller yükleniyor...", end=" ", flush=True)
    m1g  = MLClient(variant="shap_1g")
    matr = MLClient(variant="shap_atr")
    m5g  = MLClient(variant="shap_5g")
    modeller_ok = sum([m1g.available, matr.available, m5g.available])
    print(f"{modeller_ok}/3 model yüklendi")

    if modeller_ok == 0:
        print("  Hiç model yüklenemedi — çıkılıyor.")
        sys.exit(1)

    print(f"  BIST100 verisi çekiliyor...", end=" ", flush=True)
    bist_df = _indir("XU100.IS", period="3mo")
    print(f"{'OK' if not bist_df.empty else 'HATA'}")

    print(f"  {len(evren)} hisse taranıyor...\n")

    sonuclar = []
    for i, sym in enumerate(evren, 1):
        print(f"  [{i:>2}/{len(evren)}] {sym:<12}", end=" ", flush=True)

        df = veri_yukle(sym)
        if df.empty or len(df) < 80:
            print("veri yok — atlandı")
            continue

        # Hacim filtresi
        hacim = ortalama_hacim_tl(df)
        if hacim < min_vol_m:
            print(f"hacim düşük ({hacim:.1f}M TL)")
            continue

        # Göreli güç
        rs20 = goreli_guc(df, bist_df, 20)
        rs5  = goreli_guc(df, bist_df, 5)

        # ML tahminleri — sadece son gün
        son_tarih = df.index[-1].date()

        def tahmin(client, df):
            try:
                p = client.predict(sym, df, target_date=pd.Timestamp(son_tarih))
                if not p or p.get("label") == "BEKLE" and p.get("prob_bekle", 1) == 1.0:
                    p = client.predict(sym, df)
                return p
            except Exception:
                return {"signal": 1, "label": "BEKLE", "prob_al": 0.0, "prob_sat": 0.0}

        p1g  = tahmin(m1g, df)  if m1g.available  else None
        patr = tahmin(matr, df) if matr.available  else None
        p5g  = tahmin(m5g, df)  if m5g.available   else None

        # Konsensüs: kaç model AL diyor?
        consensus = sum([
            1 if p1g  and p1g.get("signal")  == 2 else 0,
            1 if patr and patr.get("signal") == 2 else 0,
            1 if p5g  and p5g.get("signal")  == 2 else 0,
        ])

        # Genel sıralama skoru
        prob_al_ort = sum(filter(None, [
            p1g.get("prob_al", 0)  if p1g  else None,
            patr.get("prob_al", 0) if patr else None,
            p5g.get("prob_al", 0)  if p5g  else None,
        ])) / modeller_ok

        son_fiyat = round(float(df["Close"].iloc[-1]), 2)

        # Zımni hedef fiyatlar (model eğitim eşiklerine göre)
        atr_val  = atr14(df)
        atr_oran = min(max(0.5 * atr_val / son_fiyat, 0.01), 0.04) if son_fiyat > 0 else 0.02
        hedef_1g  = round(son_fiyat * 1.02, 2)
        hedef_atr = round(son_fiyat * (1 + atr_oran), 2)
        hedef_5g  = round(son_fiyat * 1.02, 2)

        sonuc = {
            "sym":         sym,
            "sektor":      SEKTORLER.get(sym, "-"),
            "fiyat":       son_fiyat,
            "consensus":   consensus,
            "prob_al_ort": prob_al_ort,
            "p1g_al":      p1g.get("prob_al", 0)  if p1g  else 0,
            "p1g_label":   p1g.get("label", "-")  if p1g  else "-",
            "patr_al":     patr.get("prob_al", 0) if patr else 0,
            "patr_label":  patr.get("label", "-") if patr else "-",
            "p5g_al":      p5g.get("prob_al", 0)  if p5g  else 0,
            "p5g_label":   p5g.get("label", "-")  if p5g  else "-",
            "rs20":        rs20,
            "rs5":         rs5,
            "hacim_m":     hacim,
            "hedef_1g":    hedef_1g,
            "hedef_atr":   hedef_atr,
            "hedef_5g":    hedef_5g,
            "atr_oran":    round(atr_oran * 100, 2),
        }
        sonuclar.append(sonuc)

        kons_str = "█" * consensus + "░" * (3 - consensus)
        print(f"{kons_str}  1g:{p1g.get('prob_al',0):.0%}  "
              f"ATR:{patr.get('prob_al',0):.0%}  "
              f"5g:{p5g.get('prob_al',0):.0%}  "
              f"RS:{rs20:.2f}  {hacim:.0f}M TL")

    # Filtrele ve sırala
    sonuclar = [s for s in sonuclar if s["consensus"] >= min_consensus]
    sonuclar.sort(key=lambda x: (x["consensus"], x["prob_al_ort"], x["rs20"]),
                  reverse=True)

    if top_n > 0:
        sonuclar = sonuclar[:top_n]
    return sonuclar


def tablo_yazdir(sonuclar: list[dict]):
    if not sonuclar:
        print("\n  Kriterleri karşılayan hisse bulunamadı.")
        return

    # Gruplara ayır
    guclu_al  = [s for s in sonuclar if s["consensus"] == 3]
    al        = [s for s in sonuclar if s["consensus"] == 2]
    zayif_al  = [s for s in sonuclar if s["consensus"] == 1]

    baslik = f"{'Sıra':<5}{'Hisse':<10}{'Sektör':<16}{'Kons':>5}  {'1g':>5}{'ATR':>6}{'5g':>6}  {'RS20':>6}{'RS5':>5}  {'Fiyat':>8}  {'Hacim':>7}"
    ayrac  = "─" * len(baslik)

    def satir_yaz(i, s):
        kons = "█" * s["consensus"] + "░" * (3 - s["consensus"])
        rs20_str = f"{s['rs20']:.2f}" + (" ▲" if s["rs20"] > 1.05 else " ▼" if s["rs20"] < 0.95 else "  ")
        rs5_str  = f"{s['rs5']:.2f}"  + (" ▲" if s["rs5"]  > 1.05 else " ▼" if s["rs5"]  < 0.95 else "  ")
        print(f"  {i:<5}{s['sym'].replace('.IS',''):<10}{s['sektor']:<16}"
              f"{kons:>5}  "
              f"{s['p1g_al']:>4.0%} {s['patr_al']:>5.0%} {s['p5g_al']:>5.0%}  "
              f"{rs20_str:>6}{rs5_str:>7}  "
              f"{s['fiyat']:>8.2f}  {s['hacim_m']:>5.0f}M")

    sira = 1
    for grup, baslik_str in [(guclu_al, "GÜÇLÜ AL — 3 Model Konsensüs"),
                              (al,       "AL — 2 Model Konsensüs"),
                              (zayif_al, "ZAYIF AL — 1 Model")]:
        if not grup:
            continue
        print(f"\n  ── {baslik_str} ({len(grup)} hisse) " + "─" * 30)
        print(f"  {baslik}")
        print(f"  {ayrac}")
        for s in grup:
            satir_yaz(sira, s)
            sira += 1


def main():
    parser = argparse.ArgumentParser(description="BIST ML Günlük Tarama")
    parser.add_argument("--min-vol",       type=float, default=5.0,
                        help="Min günlük hacim (M TL, varsayılan: 5)")
    parser.add_argument("--min-consensus", type=int,   default=1,
                        help="Min kaç model AL demeli (1-3, varsayılan: 1)")
    parser.add_argument("--top",           type=int,   default=0,
                        help="En iyi N hisseyi göster (0=tümü)")
    parser.add_argument("--symbols",       nargs="+",  default=None,
                        help="Belirli hisseler (varsayılan: dinamik evren)")
    parser.add_argument("--universe-size", type=int,   default=100,
                        dest="universe_size",
                        help="Kaç hisse taransın (varsayılan: 100)")
    parser.add_argument("--sabit-liste",   action="store_true",
                        dest="sabit_liste",
                        help="Bigpara yerine sabit listeyi kullan")
    args = parser.parse_args()

    print("=" * 68)
    print(f"  BIST ML Günlük Tarama — {datetime.now().strftime('%d %B %Y, %H:%M')}")
    print(f"  Min Hacim: {args.min_vol}M TL  |  Min Konsensüs: {args.min_consensus}/3")
    print("=" * 68)

    if args.symbols:
        semboller = args.symbols
    elif args.sabit_liste:
        semboller = BIST_EVREN
    else:
        from data_feed.universe import get_universe
        semboller = get_universe(top_n=args.universe_size)

    sonuclar = tara(
        min_vol_m=args.min_vol,
        min_consensus=args.min_consensus,
        top_n=args.top,
        semboller=semboller,
    )

    print("\n" + "=" * 68)
    print(f"  SONUÇLAR — {len(sonuclar)} hisse")
    print("=" * 68)
    tablo_yazdir(sonuclar)
    print()


if __name__ == "__main__":
    main()
