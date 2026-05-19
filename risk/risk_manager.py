import logging
from storage import repositories as repo
from config import config

logger = logging.getLogger(__name__)


def daily_loss_limit_hit(broker) -> bool:
    balance = broker.get_balance()
    max_loss = config.initial_capital * config.max_daily_loss_pct
    if balance.daily_pnl < -max_loss:
        logger.warning(f"Günlük kayıp limitine ulaşıldı: {balance.daily_pnl:.0f} TL")
        return True
    return False


def can_open_position(symbol: str, quantity: int, price: float, broker) -> tuple[bool, str]:
    # Nakit kontrolü
    cost = quantity * price * (1 + config.commission_rate)
    if cost > broker.get_cash():
        return False, "Yetersiz nakit"

    # Aynı hissede zaten pozisyon var
    pos = repo.get_open_position(symbol)
    if pos:
        return False, f"{symbol} pozisyonu zaten açık"

    # Maksimum açık pozisyon sayısı
    open_positions = repo.get_all_open_positions()
    if len(open_positions) >= config.max_open_positions:
        return False, f"Maks pozisyon sayısına ulaşıldı ({config.max_open_positions})"

    # Pozisyon büyüklük kontrolü
    max_investment = config.initial_capital * config.max_position_pct
    if cost > max_investment:
        return False, f"Pozisyon büyüklüğü limiti aşıldı (max {max_investment:.0f} TL)"

    return True, "OK"


def check_stop_loss_take_profit(current_prices: dict[str, float], broker) -> list[str]:
    triggered = []
    for pos in repo.get_all_open_positions():
        price = current_prices.get(pos.symbol)
        if not price:
            continue

        pnl_pct = (price - pos.avg_cost) / pos.avg_cost

        if pnl_pct <= -config.stop_loss_pct:
            logger.warning(f"STOP-LOSS tetiklendi: {pos.symbol} ({pnl_pct:.1%})")
            broker.sell(pos.symbol, pos.quantity, price, source="auto")
            triggered.append(pos.symbol)

        elif pnl_pct >= config.take_profit_pct:
            logger.info(f"TAKE-PROFIT tetiklendi: {pos.symbol} ({pnl_pct:.1%})")
            broker.sell(pos.symbol, pos.quantity, price, source="auto")
            triggered.append(pos.symbol)

    return triggered
