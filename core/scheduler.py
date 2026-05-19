import logging
import time
from core import bot_state, market_hours
from data_feed import price_fetcher, data_cache
from data_feed.bist30_symbols import BIST30_SYMBOLS
from analysis import indicators, signal_generator
from ai_engine import claude_client
from risk import risk_manager, portfolio_calculator
from storage import repositories as repo
from config import config

logger = logging.getLogger(__name__)

_snapshot_counter = 0


def run_cycle(broker):
    global _snapshot_counter

    if not bot_state.is_running():
        return

    # Piyasa saati kontrolü
    if not market_hours.is_market_open():
        logger.debug("Piyasa kapalı, bekleniyor...")
        return

    # Gün sonu zorunlu kapanış
    if market_hours.is_force_close_time():
        logger.info("Gün sonu — tüm pozisyonlar kapatılıyor")
        prices = _fetch_current_prices()
        broker.close_all_positions(prices)
        return

    # Günlük kayıp limiti kontrolü
    if risk_manager.daily_loss_limit_hit(broker):
        logger.warning("Günlük kayıp limitine ulaşıldı — bot duraklatıldı")
        bot_state.set_status("PAUSED")
        return

    # Fiyatları çek ve stop-loss / take-profit kontrol et
    current_prices = _fetch_current_prices()
    risk_manager.check_stop_loss_take_profit(current_prices, broker)

    # İzleme listesindeki hisseleri tara
    symbols = repo.get_active_symbols() or BIST30_SYMBOLS[:5]

    for symbol in symbols:
        if not bot_state.is_running():
            break
        _process_symbol(symbol, broker, current_prices.get(symbol, 0))

    # Periyodik snapshot
    _snapshot_counter += 1
    if _snapshot_counter >= config.snapshot_interval_minutes:
        _snapshot_counter = 0
        balance = broker.get_balance()
        open_positions = repo.get_all_open_positions()
        repo.save_snapshot(
            cash=broker.get_cash(),
            total_value=balance.total_value,
            daily_pnl=balance.daily_pnl,
            daily_pnl_pct=balance.daily_pnl_pct,
            open_positions_count=len(open_positions),
        )


def _fetch_current_prices() -> dict[str, float]:
    symbols = repo.get_active_symbols() or BIST30_SYMBOLS[:5]
    return price_fetcher.get_prices_batch(symbols)


def _process_symbol(symbol: str, broker, current_price: float):
    df = price_fetcher.get_ohlcv(symbol)
    if df.empty:
        return

    df = indicators.compute_all(df)
    ind = indicators.latest_values(df)
    if not ind:
        return

    signal = signal_generator.evaluate(symbol, ind)

    # Mevcut pozisyonda stop/take zaten kontrol edildi
    # Sadece NONE değilse Claude'a gönder
    if signal.candidate == "NONE":
        return

    context = portfolio_calculator.get_portfolio_context(symbol, broker)
    decision = claude_client.decide(signal, context)

    repo.save_decision(
        symbol=symbol,
        action=decision.action,
        confidence=decision.confidence,
        reasoning=decision.reasoning,
        rsi=ind.get("rsi"),
        macd_signal=ind.get("macd_cross"),
        volume_ratio=ind.get("volume_ratio"),
    )

    price = ind["close"]

    if decision.action == "BUY" and decision.confidence >= 0.6:
        qty = portfolio_calculator.position_size(price, decision.suggested_size_pct, broker.get_cash())
        if qty > 0:
            ok, reason = risk_manager.can_open_position(symbol, qty, price, broker)
            if ok:
                broker.buy(symbol, qty, price, source="auto")
            else:
                logger.info(f"BUY engellendi ({symbol}): {reason}")

    elif decision.action == "SELL" and decision.confidence >= 0.6:
        pos = repo.get_open_position(symbol)
        if pos:
            broker.sell(symbol, pos.quantity, price, source="auto")


def start_loop(broker):
    bot_state.set_status("RUNNING")
    logger.info("Bot başlatıldı")

    while True:
        try:
            run_cycle(broker)
        except Exception as e:
            logger.error(f"Döngü hatası: {e}", exc_info=True)

        time.sleep(config.scan_interval_seconds)
