"""
BIST ML Tarama Arayüzü — Streamlit

Çalıştırmak için:
    streamlit run screener_ui.py --server.port 8502
"""

import json
import os
import time

import pandas as pd
import streamlit as st

from data_feed.universe import BIST_EVREN_GENIS, get_universe

# ── Ayarlar ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BIST ML Tarama",
    page_icon="📊",
    layout="wide",
)

AYAR_DOSYASI = "data/screener_ayarlar.json"
os.makedirs("data", exist_ok=True)

TUM_HISSELER = sorted(set(
    [f"{k}.IS" if not k.endswith(".IS") else k for k in BIST_EVREN_GENIS]
))


# ── Kalıcı ayarları yükle / kaydet ──────────────────────────────────────────
def ayar_yukle() -> dict:
    if os.path.exists(AYAR_DOSYASI):
        with open(AYAR_DOSYASI) as f:
            return json.load(f)
    return {"devre_disi": [], "ekstra": []}


def ayar_kaydet(ayar: dict):
    with open(AYAR_DOSYASI, "w") as f:
        json.dump(ayar, f, indent=2)


# ── Session state başlat ─────────────────────────────────────────────────────
if "ayar" not in st.session_state:
    st.session_state.ayar = ayar_yukle()
if "sonuclar" not in st.session_state:
    st.session_state.sonuclar = None
if "tarama_suresi" not in st.session_state:
    st.session_state.tarama_suresi = None


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Ayarlar")

    # Filtre ayarları
    st.subheader("Filtreler")
    min_hacim = st.slider("Min Günlük Hacim (M TL)", 1, 500, 5, 5)

    st.caption("Hangi modeller AL demeli?")
    m1g_sec  = st.checkbox("SHAP-1g  (yarın ±%2)",         value=False)
    matr_sec = st.checkbox("SHAP-ATR (adaptif eşik)",      value=False)
    m5g_sec  = st.checkbox("SHAP-5g  (5 gün ±%2)",        value=False)

    secili_modeller = []
    if m1g_sec:  secili_modeller.append("1g")
    if matr_sec: secili_modeller.append("atr")
    if m5g_sec:  secili_modeller.append("5g")

    if secili_modeller:
        st.caption(f"Seçili: {' + '.join(secili_modeller)} — hepsi AL demeli")
    else:
        st.caption("Seçim yok → konsensüs sayısına göre filtrele")
        min_consensus = st.radio("Min konsensüs", [1, 2, 3],
                                 format_func=lambda x: f"{x}/3 model", index=0,
                                 horizontal=True)

    universe_size = st.slider("Evren Büyüklüğü (top-N likit)", 20, 200, 100, 10)

    st.divider()

    # Hisse ekleme
    st.subheader("➕ Hisse Ekle")
    toplu_input = st.text_area(
        "Semboller (virgül veya satır ile ayır)",
        placeholder="BURCE, BAHKM\nMANAS\nKOZAL",
        height=90,
    ).strip().upper()
    if st.button("Ekle", use_container_width=True) and toplu_input:
        import re
        kodlar = [k.strip() for k in re.split(r"[,\n\r]+", toplu_input) if k.strip()]
        eklendi, zaten_var = [], []
        for kod in kodlar:
            sym = kod if kod.endswith(".IS") else f"{kod}.IS"
            if sym not in st.session_state.ayar["ekstra"]:
                st.session_state.ayar["ekstra"].append(sym)
                if sym in st.session_state.ayar["devre_disi"]:
                    st.session_state.ayar["devre_disi"].remove(sym)
                eklendi.append(sym.replace(".IS", ""))
            else:
                zaten_var.append(sym.replace(".IS", ""))
        ayar_kaydet(st.session_state.ayar)
        if eklendi:
            st.success(f"Eklendi: {', '.join(eklendi)}")
        if zaten_var:
            st.info(f"Zaten listede: {', '.join(zaten_var)}")

    # Ekstra hisseleri göster
    ekstra_listesi = st.session_state.ayar["ekstra"]
    if ekstra_listesi:
        st.caption(f"Eklenen hisseler ({len(ekstra_listesi)}):")
        for sym in list(ekstra_listesi):
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"**{sym.replace('.IS', '')}**")
            if col2.button("✕", key=f"sil_{sym}", help="Kaldır"):
                ekstra_listesi.remove(sym)
                ayar_kaydet(st.session_state.ayar)
                st.rerun()
    else:
        st.caption("Henüz eklenen hisse yok")

    st.divider()

    # Devre dışı bırakma
    st.subheader("🚫 Hariç Tut")
    devre_disi_input = st.text_input(
        "Hariç tut (virgülle ayır)",
        placeholder="örn: THYAO, GARAN"
    ).strip().upper()
    if st.button("Uygula", use_container_width=True) and devre_disi_input:
        for kod in devre_disi_input.split(","):
            kod = kod.strip()
            if not kod:
                continue
            sym = kod if kod.endswith(".IS") else f"{kod}.IS"
            if sym not in st.session_state.ayar["devre_disi"]:
                st.session_state.ayar["devre_disi"].append(sym)
        ayar_kaydet(st.session_state.ayar)
        st.rerun()

    devre_disi = st.session_state.ayar["devre_disi"]
    if devre_disi:
        st.caption(f"Hariç tutulanlar ({len(devre_disi)}):")
        for sym in list(devre_disi):
            col1, col2 = st.columns([3, 1])
            col1.write(sym.replace(".IS", ""))
            if col2.button("✕", key=f"ac_{sym}", help="Geri ekle"):
                devre_disi.remove(sym)
                ayar_kaydet(st.session_state.ayar)
                st.rerun()


# ── Ana Alan ─────────────────────────────────────────────────────────────────
st.title("📊 BIST ML Günlük Tarama")

col_btn, col_info = st.columns([1, 3])
calistir = col_btn.button("▶ Çalıştır", type="primary", use_container_width=True)

if st.session_state.tarama_suresi:
    col_info.caption(f"Son tarama: {st.session_state.tarama_suresi}")


# ── Tarama ───────────────────────────────────────────────────────────────────
if calistir:
    from screener import tara

    ayar = st.session_state.ayar

    with st.spinner("Evren yükleniyor..."):
        universe = get_universe(top_n=universe_size)

    # Ekstra hisseleri ekle, devre dışıları çıkar
    ekstra = [s for s in ayar["ekstra"] if s not in universe]
    semboller = universe + ekstra
    semboller = [s for s in semboller if s not in ayar["devre_disi"]]

    progress = st.progress(0, text="Tarama başlıyor...")
    durum = st.empty()
    baslangic = time.time()

    def on_progress(i, total, sym):
        pct = i / total
        progress.progress(pct, text=f"[{i}/{total}] {sym.replace('.IS', '')} taranıyor...")

    import io, sys
    eski_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        sonuclar = tara(
            min_vol_m=min_hacim,
            min_consensus=1,
            top_n=0,
            semboller=semboller,
            on_progress=on_progress,
        )
    finally:
        sys.stdout = eski_stdout

    progress.progress(1.0, text="Tamamlandı!")
    gecen = time.time() - baslangic
    st.session_state.tarama_suresi = (
        f"{len(semboller)} hisse — {gecen:.0f} saniye — "
        f"{pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')}"
    )
    st.session_state.sonuclar = sonuclar
    st.session_state.secili_modeller_son = secili_modeller
    st.session_state.min_consensus_filtre = locals().get("min_consensus", 1)
    time.sleep(0.3)
    st.rerun()


# ── Sonuçları Göster ─────────────────────────────────────────────────────────
if st.session_state.sonuclar is not None:
    sonuclar = st.session_state.sonuclar
    min_c = st.session_state.get("min_consensus_filtre", 1)

    # Konsensüs filtresi uygula
    # Model filtresi uygula
    secili = st.session_state.get("secili_modeller_son", [])
    if secili:
        def model_eslesiyor(s):
            if "1g"  in secili and s["p1g_label"]  != "AL": return False
            if "atr" in secili and s["patr_label"] != "AL": return False
            if "5g"  in secili and s["p5g_label"]  != "AL": return False
            return True
        filtrelenmis = [s for s in sonuclar if model_eslesiyor(s)]
    else:
        min_c = st.session_state.get("min_consensus_filtre", 1)
        filtrelenmis = [s for s in sonuclar if s["consensus"] >= min_c]

    if not filtrelenmis:
        st.warning("Kriterleri karşılayan hisse bulunamadı.")
    else:
        # DataFrame oluştur
        rows = []
        for s in filtrelenmis:
            # Model isimleri göster: AL ise renkli ✓, değilse ✗
            def model_etiketi(label, isim):
                return f"✓{isim}" if label == "AL" else f"✗{isim}"
            kons_str = "  ".join([
                model_etiketi(s["p1g_label"],  "1g"),
                model_etiketi(s["patr_label"], "ATR"),
                model_etiketi(s["p5g_label"],  "5g"),
            ])
            rs20_ok = "▲" if s["rs20"] > 1.05 else ("▼" if s["rs20"] < 0.95 else "")
            rs5_ok  = "▲" if s["rs5"]  > 1.05 else ("▼" if s["rs5"]  < 0.95 else "")

            def _hdf(label, hedef):
                return f"{hedef:.2f}" if label == "AL" else "—"

            rows.append({
                "Hisse":    s["sym"].replace(".IS", ""),
                "Sektör":   s["sektor"],
                "Modeller": kons_str,
                "1g %":     f"{s['p1g_al']:.0%}",
                "ATR %":    f"{s['patr_al']:.0%}",
                "5g %":     f"{s['p5g_al']:.0%}",
                "RS20":     f"{s['rs20']:.2f} {rs20_ok}",
                "RS5":      f"{s['rs5']:.2f} {rs5_ok}",
                "Fiyat":    f"{s['fiyat']:.2f}",
                "ATR Hdf":  _hdf(s["patr_label"], s.get("hedef_atr", 0)),
                "Hacim":    f"{s['hacim_m']:.0f}M",
                "_consensus": s["consensus"],
            })

        df = pd.DataFrame(rows)

        GRUP_RENK = {
            3: ("background-color: #1a3a1a", "color: #7fff7f"),
            2: ("background-color: #2a2a0a", "color: #ffff7f"),
            1: ("background-color: #1a1a1a", "color: #aaaaaa"),
        }

        # Gruplar halinde göster
        for c_val, baslik in [
            (3, "🟢 GÜÇLÜ AL — SHAP-1g + SHAP-ATR + SHAP-5g"),
            (2, "🟡 AL — 2 Model"),
            (1, "⚪ ZAYIF AL — 1 Model"),
        ]:
            grup = df[df["_consensus"] == c_val].copy()
            if grup.empty:
                continue
            gosterim = grup.drop(columns=["_consensus"]).reset_index(drop=True)

            bg, fg = GRUP_RENK[c_val]
            styled = gosterim.style.set_properties(**{
                "background-color": bg.split(": ")[1],
                "color": fg.split(": ")[1],
            })

            st.markdown(f"#### {baslik} &nbsp; `{len(grup)}`")
            st.dataframe(
                styled,
                use_container_width=True,
                hide_index=True,
                height=min(35 * len(grup) + 38, 600),
            )
            st.markdown("")

        # Özet
        st.divider()
        guclu = len(df[df["_consensus"] == 3])
        al    = len(df[df["_consensus"] == 2])
        zayif = len(df[df["_consensus"] == 1])
        st.markdown(
            f"**Toplam:** {len(filtrelenmis)} hisse &nbsp;|&nbsp; "
            f"🟢 Güçlü AL: **{guclu}** &nbsp;|&nbsp; "
            f"🟡 AL: **{al}** &nbsp;|&nbsp; "
            f"⚪ Zayıf AL: **{zayif}**"
        )
