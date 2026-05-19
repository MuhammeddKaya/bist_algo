from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class OrderResult:
    success: bool
    symbol: str
    side: str
    quantity: int
    price: float
    commission: float
    error: Optional[str] = None


@dataclass
class PortfolioBalance:
    cash: float
    total_value: float
    daily_pnl: float
    daily_pnl_pct: float


class BrokerInterface(ABC):

    @abstractmethod
    def buy(self, symbol: str, quantity: int, price: float, source: str = "auto") -> OrderResult:
        ...

    @abstractmethod
    def sell(self, symbol: str, quantity: int, price: float, source: str = "auto") -> OrderResult:
        ...

    @abstractmethod
    def get_balance(self) -> PortfolioBalance:
        ...

    @abstractmethod
    def get_cash(self) -> float:
        ...
