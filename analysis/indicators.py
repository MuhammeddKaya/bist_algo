import logging
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 30:
        return df

    df = df.copy()

    # RSI(14)
    df.ta.rsi(length=14, append=True)

    # MACD(12, 26, 9)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)

    # Gerçek MACD crossover (önceki bar → bu bar geçişi)
    macd_col  = next((c for c in df.columns if c.startswith("MACD_") and "s_" not in c and "h_" not in c), None)
    macds_col = next((c for c in df.columns if c.startswith("MACDs_")), None)
    if macd_col and macds_col:
        cross_up   = (df[macd_col].shift(1) <= df[macds_col].shift(1)) & (df[macd_col] > df[macds_col])
        cross_down = (df[macd_col].shift(1) >= df[macds_col].shift(1)) & (df[macd_col] < df[macds_col])
        # Son 3 mum içinde crossover olduysa "taze"
        df["macd_fresh_up"]   = cross_up.rolling(3, min_periods=1).max().astype(bool)
        df["macd_fresh_down"] = cross_down.rolling(3, min_periods=1).max().astype(bool)

    # EMA(9) ve EMA(21)
    df.ta.ema(length=9, append=True)
    df.ta.ema(length=21, append=True)

    # Bollinger Bands(20, 2) — mean reversion stratejisi için
    df.ta.bbands(length=20, std=2, append=True)

    # Hacim ortalaması (20 periyot)
    df["Volume_MA20"] = df["Volume"].rolling(20).mean()

    return df


def latest_values(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    row = df.iloc[-1]

    rsi_col   = next((c for c in df.columns if c.startswith("RSI_")), None)
    macd_col  = next((c for c in df.columns if c.startswith("MACD_") and "s_" not in c and "h_" not in c), None)
    macds_col = next((c for c in df.columns if c.startswith("MACDs_")), None)
    ema9_col  = next((c for c in df.columns if c == "EMA_9"), None)
    ema21_col = next((c for c in df.columns if c == "EMA_21"), None)
    bbl_col   = next((c for c in df.columns if c.startswith("BBL_")), None)
    bbm_col   = next((c for c in df.columns if c.startswith("BBM_")), None)
    bbu_col   = next((c for c in df.columns if c.startswith("BBU_")), None)

    rsi      = float(row[rsi_col])   if rsi_col   and pd.notna(row[rsi_col])   else None
    macd_val = float(row[macd_col])  if macd_col  and pd.notna(row[macd_col])  else None
    macd_sig = float(row[macds_col]) if macds_col and pd.notna(row[macds_col]) else None
    ema9     = float(row[ema9_col])  if ema9_col  and pd.notna(row[ema9_col])  else None
    ema21    = float(row[ema21_col]) if ema21_col and pd.notna(row[ema21_col]) else None
    bb_lower = float(row[bbl_col])   if bbl_col   and pd.notna(row[bbl_col])   else None
    bb_mid   = float(row[bbm_col])   if bbm_col   and pd.notna(row[bbm_col])   else None
    bb_upper = float(row[bbu_col])   if bbu_col   and pd.notna(row[bbu_col])   else None
    close    = float(row["Close"])
    open_    = float(row["Open"]) if "Open" in df.columns and pd.notna(row.get("Open")) else close
    volume   = float(row["Volume"])
    vol_ma   = float(row["Volume_MA20"]) if pd.notna(row.get("Volume_MA20", float("nan"))) else None

    fresh_up   = bool(row.get("macd_fresh_up",   False))
    fresh_down = bool(row.get("macd_fresh_down", False))
    # Çakışma varsa anlık MACD pozisyonu belirler: yalnızca MACD hâlâ sinyalin üstündeyse UP
    if fresh_up and macd_val is not None and macd_sig is not None and macd_val > macd_sig:
        macd_cross = "UP"
    elif fresh_down and macd_val is not None and macd_sig is not None and macd_val < macd_sig:
        macd_cross = "DOWN"
    else:
        macd_cross = None

    return {
        "open":         open_,
        "close":        close,
        "rsi":          rsi,
        "macd":         macd_val,
        "macd_signal":  macd_sig,
        "macd_cross":   macd_cross,
        "ema9":         ema9,
        "ema21":        ema21,
        "bb_lower":     bb_lower,
        "bb_mid":       bb_mid,
        "bb_upper":     bb_upper,
        "volume":       volume,
        "volume_ma20":  vol_ma,
        "volume_ratio": (volume / vol_ma) if vol_ma and vol_ma > 0 else None,
    }
