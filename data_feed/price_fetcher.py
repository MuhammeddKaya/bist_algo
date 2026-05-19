import logging
import yfinance as yf
import pandas as pd
from data_feed import data_cache
from config import config

logger = logging.getLogger(__name__)


def get_ohlcv(symbol: str, use_cache: bool = True) -> pd.DataFrame:
    if use_cache:
        cached = data_cache.get(symbol)
        if cached is not None:
            return cached

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=config.data_period, interval=config.data_interval)
        if df.empty:
            logger.warning(f"{symbol} için veri boş döndü")
            return pd.DataFrame()
        df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
        data_cache.set(symbol, df)
        return df
    except Exception as e:
        logger.error(f"{symbol} veri çekme hatası: {e}")
        return pd.DataFrame()


def get_current_price(symbol: str) -> float:
    df = get_ohlcv(symbol, use_cache=False)
    if df.empty:
        return 0.0
    return float(df["Close"].iloc[-1])


def get_prices_batch(symbols: list[str]) -> dict[str, float]:
    prices = {}
    for sym in symbols:
        price = get_current_price(sym)
        if price > 0:
            prices[sym] = price
    return prices
