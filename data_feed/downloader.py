"""
BIST veri indirici — parquet olarak data/market/ klasörüne kaydeder.

Kullanım:
    python -m data_feed.downloader              # 1m (7 gün) + 5m (60 gün)
    python -m data_feed.downloader --interval 1m
    python -m data_feed.downloader --interval 5m
"""
import argparse
import datetime
import os
import sys
import yfinance as yf
import pandas as pd
from data_feed.bist30_symbols import BIST30_SYMBOLS, display_name

MARKET_OPEN  = datetime.time(10, 0)
MARKET_CLOSE = datetime.time(17, 15)

INTERVAL_CONFIG = {
    "1m":  {"period": "7d",  "label": "Son 7 gün"},
    "2m":  {"period": "60d", "label": "Son 60 gün"},
    "5m":  {"period": "60d", "label": "Son 60 gün"},
    "15m": {"period": "60d", "label": "Son 60 gün"},
    "1h":  {"period": "2y",  "label": "Son 2 yıl"},
    "1d":  {"period": "5y",  "label": "Son 5 yıl"},
}


def save_dir(interval: str) -> str:
    path = os.path.join("data", "market", interval)
    os.makedirs(path, exist_ok=True)
    return path


def download_symbol(symbol: str, interval: str, period: str) -> pd.DataFrame | None:
    try:
        df = yf.download(symbol, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        if interval not in ("1d", "1wk", "1mo"):
            df = df.between_time(MARKET_OPEN.strftime("%H:%M"), MARKET_CLOSE.strftime("%H:%M"))
        df = df.dropna(subset=["Close", "Volume"])
        return df
    except Exception as e:
        print(f"  HATA {symbol}: {e}")
        return None


def run(intervals: list[str], symbols: list[str]):
    for interval in intervals:
        cfg = INTERVAL_CONFIG.get(interval)
        if not cfg:
            print(f"Bilinmeyen interval: {interval}. Geçerli: {list(INTERVAL_CONFIG)}")
            continue

        out_dir = save_dir(interval)
        print(f"\n{'='*60}")
        print(f"  {interval} veri  |  {cfg['label']}  →  {out_dir}")
        print(f"{'='*60}")

        ok = 0
        for sym in symbols:
            df = download_symbol(sym, interval, cfg["period"])
            if df is None or len(df) < 10:
                print(f"  {sym:<14} yetersiz/boş veri")
                continue

            path = os.path.join(out_dir, f"{sym}.csv")
            df.to_csv(path)
            date_range = f"{df.index[0].strftime('%d/%m/%y')} – {df.index[-1].strftime('%d/%m/%y')}"
            print(f"  {sym:<14} {len(df):>6} satır  {date_range}  → kaydedildi")
            ok += 1

        print(f"\n  Toplam: {ok}/{len(symbols)} hisse indirildi")
        print(f"  Klasör: {os.path.abspath(out_dir)}")


def main():
    parser = argparse.ArgumentParser(description="BIST veri indirici")
    parser.add_argument("--interval", nargs="+", default=["1m", "5m"],
                        help="Veri aralığı (varsayılan: 1m 5m)")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Hisse listesi (varsayılan: tüm BIST-30)")
    args = parser.parse_args()

    symbols = args.symbols or BIST30_SYMBOLS
    print(f"İndirilecek hisseler ({len(symbols)}): {', '.join(s.replace('.IS','') for s in symbols)}")
    run(args.interval, symbols)
    print("\nTamamlandı.")


if __name__ == "__main__":
    main()
