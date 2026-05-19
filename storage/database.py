import os
from storage.models import db, Trade, Position, AIDecision, PortfolioSnapshot, Watchlist, BotState
from config import config


def init_db():
    os.makedirs(os.path.dirname(config.db_path), exist_ok=True)
    db.init(config.db_path, pragmas={"journal_mode": "wal", "foreign_keys": 1})
    db.connect(reuse_if_open=True)
    db.create_tables([Trade, Position, AIDecision, PortfolioSnapshot, Watchlist, BotState], safe=True)

    # İlk BotState kaydı yoksa oluştur
    if not BotState.select().exists():
        BotState.create(status="STOPPED", mode=config.trading_mode)

    # İlk PortfolioSnapshot yoksa oluştur
    if not PortfolioSnapshot.select().exists():
        PortfolioSnapshot.create(
            cash=config.initial_capital,
            total_value=config.initial_capital,
            daily_pnl=0.0,
            daily_pnl_pct=0.0,
            open_positions_count=0,
        )


def get_db():
    if db.is_closed():
        db.connect(reuse_if_open=True)
    return db
