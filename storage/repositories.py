import datetime
from typing import Optional
from storage.models import Trade, Position, AIDecision, PortfolioSnapshot, Watchlist, BotState
from config import config


# --- Trade ---

def save_trade(symbol: str, side: str, quantity: int, price: float, source: str = "auto") -> Trade:
    commission = quantity * price * config.commission_rate
    total_cost = quantity * price + (commission if side == "BUY" else -commission)
    return Trade.create(
        symbol=symbol, side=side, quantity=quantity, price=price,
        commission=commission, total_cost=total_cost,
        source=source, mode=config.trading_mode,
    )


def get_trades(limit: int = 50):
    return list(Trade.select().order_by(Trade.timestamp.desc()).limit(limit))


# --- Position ---

def get_open_position(symbol: str) -> Optional[Position]:
    return Position.get_or_none(Position.symbol == symbol, Position.status == "OPEN")


def get_all_open_positions():
    return list(Position.select().where(Position.status == "OPEN"))


def open_position(symbol: str, quantity: int, avg_cost: float):
    existing = get_open_position(symbol)
    if existing:
        # Ortalama maliyet güncelle
        total_qty = existing.quantity + quantity
        new_avg = (existing.avg_cost * existing.quantity + avg_cost * quantity) / total_qty
        existing.quantity = total_qty
        existing.avg_cost = new_avg
        existing.total_invested = total_qty * new_avg
        existing.save()
        return existing
    return Position.create(
        symbol=symbol, quantity=quantity,
        avg_cost=avg_cost, total_invested=quantity * avg_cost,
    )


def close_position(symbol: str):
    pos = get_open_position(symbol)
    if pos:
        pos.status = "CLOSED"
        pos.closed_at = datetime.datetime.now()
        pos.save()
    return pos


# --- AIDecision ---

def save_decision(symbol: str, action: str, confidence: float, reasoning: str,
                  rsi: float = None, macd_signal: str = None, volume_ratio: float = None):
    return AIDecision.create(
        symbol=symbol, action=action, confidence=confidence,
        reasoning=reasoning, rsi=rsi, macd_signal=macd_signal,
        volume_ratio=volume_ratio,
    )


def get_decisions(limit: int = 50, action_filter: str = None):
    q = AIDecision.select().order_by(AIDecision.created_at.desc())
    if action_filter:
        q = q.where(AIDecision.action == action_filter)
    return list(q.limit(limit))


# --- PortfolioSnapshot ---

def save_snapshot(cash: float, total_value: float, daily_pnl: float,
                  daily_pnl_pct: float, open_positions_count: int):
    return PortfolioSnapshot.create(
        cash=cash, total_value=total_value,
        daily_pnl=daily_pnl, daily_pnl_pct=daily_pnl_pct,
        open_positions_count=open_positions_count,
    )


def get_latest_snapshot() -> Optional[PortfolioSnapshot]:
    return PortfolioSnapshot.select().order_by(PortfolioSnapshot.timestamp.desc()).first()


def get_snapshots(days: int = 7):
    since = datetime.datetime.now() - datetime.timedelta(days=days)
    return list(
        PortfolioSnapshot.select()
        .where(PortfolioSnapshot.timestamp >= since)
        .order_by(PortfolioSnapshot.timestamp.asc())
    )


# --- Watchlist ---

def get_active_symbols():
    return [w.symbol for w in Watchlist.select().where(Watchlist.is_active == True)]


def add_to_watchlist(symbol: str, added_by: str = "manual"):
    obj, created = Watchlist.get_or_create(symbol=symbol, defaults={"added_by": added_by})
    if not created and not obj.is_active:
        obj.is_active = True
        obj.save()
    return obj


def remove_from_watchlist(symbol: str):
    w = Watchlist.get_or_none(Watchlist.symbol == symbol)
    if w:
        w.is_active = False
        w.save()


def get_watchlist():
    return list(Watchlist.select().order_by(Watchlist.added_at.desc()))


# --- BotState ---

def get_bot_state() -> BotState:
    return BotState.select().order_by(BotState.id.desc()).first()


def set_bot_status(status: str):
    state = get_bot_state()
    if state:
        state.status = status
        state.updated_at = datetime.datetime.now()
        state.save()
    else:
        BotState.create(status=status, mode=config.trading_mode)
