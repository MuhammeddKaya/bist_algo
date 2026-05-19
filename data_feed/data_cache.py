import time
from typing import Optional
import pandas as pd

_cache: dict[str, tuple[pd.DataFrame, float]] = {}
TTL = 60  # saniye


def set(symbol: str, df: pd.DataFrame):
    _cache[symbol] = (df, time.time())


def get(symbol: str) -> Optional[pd.DataFrame]:
    entry = _cache.get(symbol)
    if entry and (time.time() - entry[1]) < TTL:
        return entry[0]
    return None


def invalidate(symbol: str):
    _cache.pop(symbol, None)


def clear():
    _cache.clear()
