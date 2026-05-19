import json
import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class TradingDecision:
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float
    reasoning: str
    suggested_size_pct: float


def parse(raw: str) -> TradingDecision:
    try:
        # JSON bloğunu bul (model bazen ```json ... ``` ile sarar)
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        data = json.loads(text)
        action = data.get("action", "HOLD").upper()
        if action not in ("BUY", "SELL", "HOLD"):
            action = "HOLD"

        return TradingDecision(
            action=action,
            confidence=float(data.get("confidence", 0.5)),
            reasoning=str(data.get("reasoning", "")),
            suggested_size_pct=float(data.get("suggested_size_pct", 0.10)),
        )
    except Exception as e:
        logger.warning(f"Karar parse hatası: {e} | Raw: {raw[:200]}")
        return TradingDecision(action="HOLD", confidence=0.0, reasoning="Parse hatası", suggested_size_pct=0.0)
