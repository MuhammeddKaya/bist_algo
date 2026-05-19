import json
import logging
import httpx
from config import config
from ai_engine.decision_parser import TradingDecision, parse

logger = logging.getLogger(__name__)


def decide(system_prompt: str, user_prompt: str) -> TradingDecision:
    url = f"{config.ollama_base_url}/api/chat"
    payload = {
        "model": config.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.3},
    }

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw = data["message"]["content"]
            decision = parse(raw)
            logger.info(f"Ollama ({config.ollama_model}) → {decision.action} (güven: {decision.confidence:.2f})")
            return decision
    except Exception as e:
        logger.error(f"Ollama hatası: {e}")
        return TradingDecision(action="HOLD", confidence=0.0,
                               reasoning=f"Ollama hatası: {e}", suggested_size_pct=0.0)
