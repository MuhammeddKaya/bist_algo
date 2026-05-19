from peewee import (
    Model, SqliteDatabase,
    AutoField, CharField, FloatField, IntegerField,
    DateTimeField, BooleanField, TextField
)
import datetime

db = SqliteDatabase(None)  # init_db() ile başlatılır


class BaseModel(Model):
    class Meta:
        database = db


class Trade(BaseModel):
    id = AutoField()
    symbol = CharField(max_length=20)
    side = CharField(max_length=4)          # BUY / SELL
    quantity = IntegerField()
    price = FloatField()
    commission = FloatField(default=0.0)
    total_cost = FloatField()               # quantity * price + commission
    source = CharField(max_length=10)       # auto / manual
    mode = CharField(max_length=5)          # paper / live
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "trades"


class Position(BaseModel):
    id = AutoField()
    symbol = CharField(max_length=20)
    quantity = IntegerField()
    avg_cost = FloatField()
    total_invested = FloatField()
    status = CharField(max_length=6, default="OPEN")   # OPEN / CLOSED
    opened_at = DateTimeField(default=datetime.datetime.now)
    closed_at = DateTimeField(null=True)

    class Meta:
        table_name = "positions"


class AIDecision(BaseModel):
    id = AutoField()
    symbol = CharField(max_length=20)
    action = CharField(max_length=4)        # BUY / SELL / HOLD
    confidence = FloatField(default=0.0)
    reasoning = TextField(default="")
    rsi = FloatField(null=True)
    macd_signal = CharField(max_length=4, null=True)   # UP / DOWN
    volume_ratio = FloatField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "ai_decisions"


class PortfolioSnapshot(BaseModel):
    id = AutoField()
    cash = FloatField()
    total_value = FloatField()
    daily_pnl = FloatField(default=0.0)
    daily_pnl_pct = FloatField(default=0.0)
    open_positions_count = IntegerField(default=0)
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "portfolio_snapshots"


class Watchlist(BaseModel):
    id = AutoField()
    symbol = CharField(max_length=20, unique=True)
    added_by = CharField(max_length=6, default="auto")  # auto / manual
    is_active = BooleanField(default=True)
    added_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "watchlist"


class BotState(BaseModel):
    id = AutoField()
    status = CharField(max_length=10, default="STOPPED")  # RUNNING / PAUSED / STOPPED
    mode = CharField(max_length=5, default="paper")        # paper / live
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "bot_state"
