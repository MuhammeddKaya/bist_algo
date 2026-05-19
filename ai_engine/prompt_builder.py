from analysis.signal_generator import SignalResult


SYSTEM_PROMPT = """Sen bir BIST (Borsa İstanbul) al-sat uzmanısın. Sana bir hisse senedinin teknik göstergelerini ve mevcut portföy durumunu vereceğim. Kararını JSON formatında vereceksin.

Kurallar:
- Yanıtın YALNIZCA geçerli bir JSON objesi olmalı, başka hiçbir metin olmamalı
- action: "BUY", "SELL" veya "HOLD"
- confidence: 0.0 ile 1.0 arasında bir sayı
- reasoning: Kararının kısa gerekçesi (max 2 cümle, Türkçe)
- suggested_size_pct: Önerilen pozisyon büyüklüğü (0.0 ile 0.20 arasında, sermayenin yüzdesi)

Örnek yanıt:
{"action": "BUY", "confidence": 0.75, "reasoning": "RSI aşırı satım bölgesinde, MACD yukarı kesiyor.", "suggested_size_pct": 0.15}
"""


def build_prompt(signal: SignalResult, portfolio_context: dict) -> tuple[str, str]:
    ind = signal.indicators
    rsi = ind.get("rsi")
    macd_cross = ind.get("macd_cross", "N/A")
    volume_ratio = ind.get("volume_ratio")
    close = ind.get("close", 0)
    ema9 = ind.get("ema9")
    ema21 = ind.get("ema21")

    has_position = portfolio_context.get("has_position", False)
    avg_cost = portfolio_context.get("avg_cost", 0)
    daily_pnl_pct = portfolio_context.get("daily_pnl_pct", 0)
    cash_available = portfolio_context.get("cash_available", 0)

    user_prompt = f"""Hisse: {signal.symbol}
Güncel Fiyat: {close:.2f} TL
RSI(14): {f"{rsi:.1f}" if rsi else "N/A"}
MACD Yönü: {macd_cross}
Hacim/Ort: {f"{volume_ratio:.2f}x" if volume_ratio else "N/A"}
EMA9: {f"{ema9:.2f}" if ema9 else "N/A"} | EMA21: {f"{ema21:.2f}" if ema21 else "N/A"}
Sinyal Skoru: {signal.score}/4 ({signal.candidate})

Portföy Durumu:
- Açık Pozisyon: {"Evet, " + str(portfolio_context.get("quantity", 0)) + " lot @ " + f"{avg_cost:.2f} TL" if has_position else "Hayır"}
- Kullanılabilir Nakit: {cash_available:.0f} TL
- Günlük P&L: {daily_pnl_pct:+.2f}%

Kararını ver (yalnızca JSON):"""

    return SYSTEM_PROMPT, user_prompt
