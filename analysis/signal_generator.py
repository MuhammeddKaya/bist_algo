from dataclasses import dataclass, field
from typing import Literal


@dataclass
class SignalResult:
    symbol:    str
    candidate: Literal["BUY", "SELL", "NONE"]
    score:     int
    strategy:  Literal["trend", "mean_rev", "none"]
    indicators: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Strateji 1 — Trend / Momentum
# ---------------------------------------------------------------------------
# Giriş (3/3 — hepsi zorunlu, RSI kapısı ayrıca):
#   • 44 ≤ RSI ≤ 63          → [ZOR KAPI] nötr-momentum bölgesi
#   • close > EMA21          → üst trend aktif
#   • MACD taze crossover UP → momentum teyidi (anlık poz: macd > signal)
#   • hacim ≥ 2.0×ort.       → güçlü katılım onayı
#
# Çıkış (2/4 yeterli):
#   • close < EMA21          → trend kırıldı
#   • MACD taze crossover DW → momentum döndü
#   • RSI > 68               → aşırı alım bölgesi
#   • hacim ≥ 1.2×ort.       → satış baskısı hacimli
# ---------------------------------------------------------------------------

def evaluate_trend(symbol: str, ind: dict) -> SignalResult:
    rsi          = ind.get("rsi")
    macd_cross   = ind.get("macd_cross")
    volume_ratio = ind.get("volume_ratio")
    close        = ind.get("close", 0)
    ema21        = ind.get("ema21")

    # ÇIKIŞ: RSI kapısı olmadan — açık pozisyonu her koşulda koruyabilelim
    sell = 0
    if close and ema21 and close < ema21:                sell += 1
    if macd_cross == "DOWN":                             sell += 1
    if rsi is not None and rsi > 68:                    sell += 1
    if volume_ratio is not None and volume_ratio >= 1.2: sell += 1
    if sell >= 2:
        return SignalResult(symbol=symbol, candidate="SELL", score=sell, strategy="trend", indicators=ind)

    # GİRİŞ: RSI zorunlu kapı — momentum bölgesinde olmalı
    if rsi is None or not (44 <= rsi <= 63):
        return SignalResult(symbol=symbol, candidate="NONE", score=0, strategy="none", indicators=ind)

    buy = 0
    if close and ema21 and close > ema21:                buy += 1
    if macd_cross == "UP":                               buy += 1
    if volume_ratio is not None and volume_ratio >= 2.0: buy += 1

    # 3/3 zorunlu — daha az sinyal, daha yüksek kalite
    if buy >= 3:
        return SignalResult(symbol=symbol, candidate="BUY", score=buy, strategy="trend", indicators=ind)
    return SignalResult(symbol=symbol, candidate="NONE", score=0, strategy="none", indicators=ind)


# ---------------------------------------------------------------------------
# Strateji 2 — Mean Reversion
# ---------------------------------------------------------------------------
# Giriş (4/5 — RSI+MACD çift kapı):
#   • RSI < 33               → [ZOR KAPI] gerçek aşırı satım
#   • MACD taze crossover UP → [ZOR KAPI] momentum dönüyor (düşen bıçak filtresi)
#   • close ≤ BB_lower×1.015 → Bollinger alt bant yakını (+1 puan)
#   • close > open           → ilk toparlanma mumu / yeşil kapanış (+1 puan)
#   • hacim ≥ 1.5×ort.       → güçlü ilgi (+1 puan)
#
# Çıkış (2/3 yeterli):
#   • RSI > 55               → iyileşme tamamlandı
#   • close ≥ BB_mid         → Bollinger orta bandına döndü
#   • MACD taze crossover DW → momentum bitti
# ---------------------------------------------------------------------------

def evaluate_mean_rev(symbol: str, ind: dict) -> SignalResult:
    rsi          = ind.get("rsi")
    volume_ratio = ind.get("volume_ratio")
    close        = ind.get("close", 0)
    open_        = ind.get("open",  close)
    bb_lower     = ind.get("bb_lower")
    bb_mid       = ind.get("bb_mid")
    macd_cross   = ind.get("macd_cross")

    # RSI zorunlu kapı: gerçek aşırı satım bölgesi
    if rsi is None or rsi >= 33:
        # Satış sinyali için RSI > 55 kontrolü (pozisyon çıkışı)
        sell = 0
        if rsi is not None and rsi > 55:                    sell += 1
        if bb_mid is not None and close >= bb_mid:          sell += 1
        if macd_cross == "DOWN":                            sell += 1
        if sell >= 2:
            return SignalResult(symbol=symbol, candidate="SELL", score=sell, strategy="mean_rev", indicators=ind)
        return SignalResult(symbol=symbol, candidate="NONE", score=0, strategy="none", indicators=ind)

    # RSI < 33 — MACD crossover UP da zorunlu: sadece RSI değil, momentum da dönmeli
    # Aksi hâlde "düşen bıçak" yakalama riski yüksek
    if macd_cross != "UP":
        return SignalResult(symbol=symbol, candidate="NONE", score=0, strategy="none", indicators=ind)

    # Her iki kapı geçildi (RSI < 33 + MACD_UP); ek koşullar 2/3 yeterli
    buy = 2  # RSI<33=1, MACD_UP=1
    if bb_lower is not None and close <= bb_lower * 1.015:  buy += 1
    if close > open_:                                       buy += 1
    if volume_ratio is not None and volume_ratio >= 1.5:    buy += 1

    sell = 0
    if rsi is not None and rsi > 55:                        sell += 1
    if bb_mid is not None and close >= bb_mid:              sell += 1
    if macd_cross == "DOWN":                                sell += 1

    if buy >= 4 and buy > sell:
        return SignalResult(symbol=symbol, candidate="BUY",  score=buy,  strategy="mean_rev", indicators=ind)
    if sell >= 2:
        return SignalResult(symbol=symbol, candidate="SELL", score=sell, strategy="mean_rev", indicators=ind)
    return SignalResult(symbol=symbol, candidate="NONE", score=0, strategy="none", indicators=ind)


# ---------------------------------------------------------------------------
# Ana giriş noktası — önce mean reversion (daha nadir, daha güçlü)
# ---------------------------------------------------------------------------

def evaluate(symbol: str, indicators: dict) -> SignalResult:
    if not indicators:
        return SignalResult(symbol=symbol, candidate="NONE", score=0, strategy="none")

    mr = evaluate_mean_rev(symbol, indicators)
    if mr.candidate != "NONE":
        return mr

    return evaluate_trend(symbol, indicators)
