import logging
import datetime
from trading.broker_interface import BrokerInterface, OrderResult, PortfolioBalance
from storage import repositories as repo
from config import config

logger = logging.getLogger(__name__)

_start_of_day_value: float | None = None


class PaperTrader(BrokerInterface):

    def __init__(self):
        snapshot = repo.get_latest_snapshot()
        self._cash = snapshot.cash if snapshot else config.initial_capital
        self._start_value = snapshot.total_value if snapshot else config.initial_capital

    def buy(self, symbol: str, quantity: int, price: float, source: str = "auto") -> OrderResult:
        commission = quantity * price * config.commission_rate
        total_cost = quantity * price + commission

        if total_cost > self._cash:
            return OrderResult(success=False, symbol=symbol, side="BUY",
                               quantity=quantity, price=price, commission=commission,
                               error="Yetersiz nakit")

        self._cash -= total_cost
        repo.open_position(symbol, quantity, price)
        repo.save_trade(symbol, "BUY", quantity, price, source)
        self._save_snapshot()

        logger.info(f"PAPER BUY: {quantity} lot {symbol} @ {price:.2f} TL | Nakit: {self._cash:.0f} TL")
        return OrderResult(success=True, symbol=symbol, side="BUY",
                           quantity=quantity, price=price, commission=commission)

    def sell(self, symbol: str, quantity: int, price: float, source: str = "auto") -> OrderResult:
        pos = repo.get_open_position(symbol)
        if not pos or pos.quantity < quantity:
            return OrderResult(success=False, symbol=symbol, side="SELL",
                               quantity=quantity, price=price, commission=0,
                               error="Yeterli pozisyon yok")

        commission = quantity * price * config.commission_rate
        proceeds = quantity * price - commission
        self._cash += proceeds

        if pos.quantity == quantity:
            repo.close_position(symbol)
        else:
            pos.quantity -= quantity
            pos.total_invested = pos.quantity * pos.avg_cost
            pos.save()

        repo.save_trade(symbol, "SELL", quantity, price, source)
        self._save_snapshot()

        logger.info(f"PAPER SELL: {quantity} lot {symbol} @ {price:.2f} TL | Nakit: {self._cash:.0f} TL")
        return OrderResult(success=True, symbol=symbol, side="SELL",
                           quantity=quantity, price=price, commission=commission)

    def close_all_positions(self, current_prices: dict[str, float]):
        for pos in repo.get_all_open_positions():
            price = current_prices.get(pos.symbol, pos.avg_cost)
            self.sell(pos.symbol, pos.quantity, price, source="auto")

    def get_cash(self) -> float:
        return self._cash

    def get_balance(self) -> PortfolioBalance:
        positions = repo.get_all_open_positions()
        position_value = sum(p.total_invested for p in positions)
        total = self._cash + position_value
        daily_pnl = total - self._start_value
        daily_pnl_pct = (daily_pnl / self._start_value * 100) if self._start_value > 0 else 0
        return PortfolioBalance(cash=self._cash, total_value=total,
                                daily_pnl=daily_pnl, daily_pnl_pct=daily_pnl_pct)

    def sync_cash(self):
        snapshot = repo.get_latest_snapshot()
        if snapshot:
            self._cash = snapshot.cash

    def _save_snapshot(self):
        balance = self.get_balance()
        positions = repo.get_all_open_positions()
        repo.save_snapshot(
            cash=self._cash,
            total_value=balance.total_value,
            daily_pnl=balance.daily_pnl,
            daily_pnl_pct=balance.daily_pnl_pct,
            open_positions_count=len(positions),
        )
