"""
BIST ML modeli — bist_model projesindeki eğitilmiş SHAP-1g XGBoost'u
günlük rejim filtresi olarak kullanır.

Kullanım:
    from ai_engine.ml_client import MLClient
    client = MLClient()
    result = client.predict(symbol, df_1d)
    # result: {"signal": 2, "label": "AL", "prob_al": 0.61, "prob_sat": 0.12}
"""

import os
import sys
import pickle
import logging
from datetime import datetime, timedelta
from functools import lru_cache

import pandas as pd
import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)

BIST_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "bist_model")
MODEL_DIR       = os.path.join(BIST_MODEL_PATH, "models")

LABELS = {0: "SAT", 1: "BEKLE", 2: "AL"}

_MAKRO_SEMBOLLER = {
    "USDTRY=X": "usdtry",
    "EURTRY=X": "eurtry",
    "XU100.IS": "bist100",
    "GC=F":     "altin",
    "BZ=F":     "brent",
    "^VIX":     "vix",
}


def _feature_hesapla(df: pd.DataFrame) -> pd.DataFrame:
    """bist_model/feature_hesapla.py ile aynı mantık — import yerine inline."""
    sys.path.insert(0, os.path.abspath(BIST_MODEL_PATH))
    try:
        from feature_hesapla import feature_hesapla
        return feature_hesapla(df)
    finally:
        if sys.path[0] == os.path.abspath(BIST_MODEL_PATH):
            sys.path.pop(0)


def _makro_feature_hesapla(makro_df: pd.DataFrame) -> pd.DataFrame:
    mf = pd.DataFrame(index=makro_df.index)
    if "usdtry" in makro_df.columns:
        mf["usdtry_degisim_1g"] = makro_df["usdtry"].pct_change(1)
        mf["usdtry_degisim_5g"] = makro_df["usdtry"].pct_change(5)
        mf["usdtry_ema10"]      = makro_df["usdtry"].ewm(span=10).mean()
        mf["usdtry_trend"]      = makro_df["usdtry"] / mf["usdtry_ema10"]
        mf["usdtry_volatilite"] = makro_df["usdtry"].pct_change().rolling(10).std()
    if "eurtry" in makro_df.columns:
        mf["eurtry_degisim_1g"] = makro_df["eurtry"].pct_change(1)
        mf["eurtry_degisim_5g"] = makro_df["eurtry"].pct_change(5)
    if "bist100" in makro_df.columns:
        mf["bist100_degisim_1g"] = makro_df["bist100"].pct_change(1)
        mf["bist100_degisim_5g"] = makro_df["bist100"].pct_change(5)
        mf["bist100_ema20"]      = makro_df["bist100"].ewm(span=20).mean()
        mf["bist100_trend"]      = makro_df["bist100"] / mf["bist100_ema20"]
    if "altin" in makro_df.columns:
        mf["altin_degisim_1g"] = makro_df["altin"].pct_change(1)
        mf["altin_degisim_5g"] = makro_df["altin"].pct_change(5)
    if "brent" in makro_df.columns:
        mf["brent_degisim_1g"] = makro_df["brent"].pct_change(1)
        mf["brent_degisim_5g"] = makro_df["brent"].pct_change(5)
    if "vix" in makro_df.columns:
        mf["vix"]            = makro_df["vix"]
        mf["vix_degisim_1g"] = makro_df["vix"].pct_change(1)
        mf["vix_yuksek"]     = (makro_df["vix"] > 25).astype(int)
        mf["vix_cok_yuksek"] = (makro_df["vix"] > 35).astype(int)
    return mf


def _makro_indir(baslangic: str, bitis: str) -> pd.DataFrame:
    makro_df = pd.DataFrame()
    for sembol, isim in _MAKRO_SEMBOLLER.items():
        try:
            raw = yf.download(sembol, start=baslangic, end=bitis,
                              interval="1d", progress=False, auto_adjust=True)
            if raw.empty:
                continue
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            seri = raw["Close"].rename(isim)
            seri.index = pd.to_datetime(seri.index).tz_localize(None)
            makro_df = seri.to_frame() if makro_df.empty else makro_df.join(seri, how="outer")
        except Exception as e:
            logger.debug("Makro veri hatası %s: %s", sembol, e)
    makro_df = makro_df.ffill().bfill()
    return _makro_feature_hesapla(makro_df)


class MLClient:
    """
    SHAP-1g XGBoost modelini yükler ve günlük AL/BEKLE/SAT tahmini üretir.
    Backtest'te her gün için bir kez çağrılır; live bot'ta gün başında bir kez.
    """

    def __init__(self, variant: str = "shap_1g"):
        self._model    = None
        self._features = None
        self._variant  = variant
        self._makro_cache: dict[str, pd.DataFrame] = {}
        self._load()

    def _load(self):
        prefix = {
            "shap_1g":  ("shap_1g_xgb_model.pkl",  "shap_1g_feature_listesi.pkl"),
            "shap_atr": ("shap_atr_xgb_model.pkl", "shap_atr_feature_listesi.pkl"),
            "shap_5g":  ("shap_5g_xgb_model.pkl",  "shap_5g_feature_listesi.pkl"),
            "xgb_1g":   ("xgb_model.pkl",           "feature_listesi.pkl"),
        }.get(self._variant, ("shap_1g_xgb_model.pkl", "shap_1g_feature_listesi.pkl"))

        model_path   = os.path.join(MODEL_DIR, prefix[0])
        feature_path = os.path.join(MODEL_DIR, prefix[1])

        if not os.path.exists(model_path):
            logger.error("Model bulunamadı: %s", model_path)
            return

        with open(model_path,   "rb") as f: self._model    = pickle.load(f)
        with open(feature_path, "rb") as f: self._features = pickle.load(f)
        logger.info("ML model yüklendi: %s (%d feature)", self._variant, len(self._features))

    @property
    def available(self) -> bool:
        return self._model is not None and self._features is not None

    def _get_makro(self, idx: pd.DatetimeIndex) -> pd.DataFrame:
        baslangic = (idx.min() - timedelta(days=30)).strftime("%Y-%m-%d")
        bitis     = (idx.max() + timedelta(days=2)).strftime("%Y-%m-%d")
        cache_key = f"{baslangic}_{bitis}"
        if cache_key not in self._makro_cache:
            self._makro_cache[cache_key] = _makro_indir(baslangic, bitis)
        return self._makro_cache[cache_key]

    def predict_all(self, symbol: str, df_1d: pd.DataFrame) -> dict[object, dict]:
        """
        Tüm günler için vektörize tahmin — backtest için optimize.
        Returns: {date: {"signal":..., "prob_al":...}}
        """
        if not self.available or df_1d.empty or len(df_1d) < 60:
            return {}
        try:
            df = df_1d.copy()
            df.index = pd.to_datetime(df.index).tz_localize(None)

            df = _feature_hesapla(df)

            makro = self._get_makro(df.index)
            makro = makro.reindex(df.index, method="ffill")

            extra = pd.DataFrame(index=df.index)
            if "bist100_degisim_1g" in makro.columns:
                extra["endeks_ustu_1g"] = (df["Close"].pct_change(1) - makro["bist100_degisim_1g"]).fillna(0)
                extra["endeks_ustu_5g"] = (df["Close"].pct_change(5) - makro.get("bist100_degisim_5g", 0)).fillna(0)

            df = pd.concat([df, makro, extra], axis=1)
            df = df.iloc[60:]   # ısınma dönemi

            X = df.reindex(columns=self._features, fill_value=0).fillna(0)
            probs_all = self._model.predict_proba(X)   # shape (n, 3)

            result = {}
            for i, (ts, probs) in enumerate(zip(df.index, probs_all)):
                pred = int(probs.argmax())
                result[ts.date()] = {
                    "signal":     pred,
                    "label":      LABELS[pred],
                    "prob_sat":   float(probs[0]),
                    "prob_bekle": float(probs[1]),
                    "prob_al":    float(probs[2]),
                }
            return result
        except Exception as e:
            logger.warning("ML tahmin hatası (%s): %s", symbol, e)
            return {}

    def predict(self, symbol: str, df_1d: pd.DataFrame,
                target_date: pd.Timestamp | None = None) -> dict:
        """Son satır veya verilen tarihe ait tekil tahmin — live bot için."""
        _EMPTY = {"signal": 1, "label": "BEKLE",
                  "prob_sat": 0.0, "prob_bekle": 1.0, "prob_al": 0.0}
        preds = self.predict_all(symbol, df_1d)
        if not preds:
            return _EMPTY
        if target_date is not None:
            return preds.get(target_date.date(), _EMPTY)
        return list(preds.values())[-1]
