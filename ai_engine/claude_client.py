import logging
import anthropic
from config import config
from analysis.signal_generator import SignalResult
from ai_engine.prompt_builder import build_prompt
from ai_engine.decision_parser import TradingDecision, parse
from ai_engine import ollama_client

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None
_anthropic_available: bool | None = None  # None = henüz test edilmedi


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    return _client


def _try_anthropic(system_prompt: str, user_prompt: str) -> TradingDecision | None:
    global _anthropic_available
    if _anthropic_available is False:
        return None
    try:
        client = _get_client()
        response = client.messages.create(
            model=config.claude_model,
            max_tokens=256,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_prompt}],
        )
        _anthropic_available = True
        return parse(response.content[0].text)
    except anthropic.AuthenticationError:
        logger.warning("Anthropic API key geçersiz — Ollama'ya geçiliyor")
        _anthropic_available = False
        return None
    except Exception as e:
        err = str(e).lower()
        if "credit" in err or "balance" in err or "billing" in err:
            logger.warning(f"Anthropic kredi yetersiz — Ollama'ya geçiliyor")
            _anthropic_available = False
            return None
        logger.error(f"Anthropic geçici hata: {e}")
        return None


def decide(signal: SignalResult, portfolio_context: dict) -> TradingDecision:
    system_prompt, user_prompt = build_prompt(signal, portfolio_context)

    # 1. Anthropic dene
    decision = _try_anthropic(system_prompt, user_prompt)
    if decision is not None:
        logger.info(f"[Claude] {signal.symbol} → {decision.action} ({decision.confidence:.0%})")
        return decision

    # 2. Ollama fallback
    logger.info(f"[Ollama/{config.ollama_model}] {signal.symbol} kararı isteniyor...")
    decision = ollama_client.decide(system_prompt, user_prompt)
    logger.info(f"[Ollama] {signal.symbol} → {decision.action} ({decision.confidence:.0%})")
    return decision
