from storage import repositories as repo
from config import config


def get_portfolio_context(symbol: str, broker) -> dict:
    pos = repo.get_open_position(symbol)
    balance = broker.get_balance()
    snapshot = repo.get_latest_snapshot()

    return {
        "has_position": pos is not None,
        "quantity": pos.quantity if pos else 0,
        "avg_cost": pos.avg_cost if pos else 0,
        "cash_available": broker.get_cash(),
        "total_value": balance.total_value,
        "daily_pnl": balance.daily_pnl,
        "daily_pnl_pct": balance.daily_pnl_pct,
    }


def position_size(price: float, suggested_pct: float, available_cash: float) -> int:
    max_investment = min(
        config.initial_capital * config.max_position_pct,
        available_cash * 0.95,  # nakit tamponunu koru
    )
    target = config.initial_capital * min(suggested_pct, config.max_position_pct)
    investment = min(target, max_investment)
    if price <= 0 or investment <= 0:
        return 0
    return max(1, int(investment / price))
