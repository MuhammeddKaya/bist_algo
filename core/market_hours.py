import datetime
from config import config


def _parse_time(t: str) -> datetime.time:
    h, m = t.split(":")
    return datetime.time(int(h), int(m))


def is_market_open() -> bool:
    now = datetime.datetime.now().time()
    start = _parse_time(config.trading_start)
    end = _parse_time(config.trading_end)
    weekday = datetime.datetime.now().weekday()
    # Pazartesi=0 ... Cuma=4
    if weekday >= 5:
        return False
    return start <= now <= end


def is_force_close_time() -> bool:
    now = datetime.datetime.now().time()
    close_time = _parse_time(config.force_close_time)
    end_time = _parse_time(config.trading_end)
    return now >= close_time or now >= end_time
