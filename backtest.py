"""
BIST intraday backtest.

Veri kaynağı: data/market/<interval>/<SYMBOL>.csv  (downloader.py ile indirilmiş)
Karar motoru: kural tabanlı + isteğe bağlı AI onayı

Kullanım:
    python backtest.py                          # 1m, kural, EOD çıkış
    python backtest.py --interval 5m            # 5m veri
    python backtest.py --exit-mode overnight    # geceye pozisyon taşı
    python backtest.py --engine ollama          # kural + Ollama onayı
"""
import argparse
import datetime
import logging
import os
from collections import defaultdict

import pandas as pd
import pandas_ta as ta

from storage.models import db, Trade, Position, AIDecision, PortfolioSnapshot, Watchlist, BotState
from storage import repositories as repo
from ai_engine.decision_parser import TradingDecision
from analysis.signal_generator import evaluate
from analysis.indicators import compute_all, latest_values
from trading.paper_trader import PaperTrader
from risk.risk_manager import can_open_position
from risk.portfolio_calculator import position_size
from config import config
from data_feed.bist30_symbols import BIST30_SYMBOLS

logging.basicConfig(level=logging.WARNING)

MARKET_OPEN  = datetime.time(10, 0)
MARKET_CLOSE = datetime.time(17, 15)

CHECK_EVERY_MAP  = {"1m": 15, "5m": 12, "15m": 4, "1h": 1}
COOLDOWN_CHECKS  = 3   # satıştan sonra kaç kontrol aralığı beklenir


def parse_hhmm(value: str | None) -> datetime.time | None:
    if not value:
        return None
    hour, minute = value.split(":", 1)
    return datetime.time(int(hour), int(minute))


def load_symbol(symbol: str, interval: str) -> pd.DataFrame:
    path = os.path.join("data", "market", interval, f"{symbol}.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.dropna(subset=["Close", "Volume"])


def rule_decision(signal) -> TradingDecision:
    action = signal.candidate if signal.candidate != "NONE" else "HOLD"
    conf   = 0.60 + signal.score * 0.05
    return TradingDecision(action=action, confidence=conf,
                           reasoning="Teknik gösterge", suggested_size_pct=0.15)


def ai_approve(signal, context: dict, engine: str) -> TradingDecision:
    from ai_engine import ollama_client, claude_client
    from ai_engine.prompt_builder import build_prompt
    sys_p, usr_p = build_prompt(signal, context)
    if engine == "ollama":
        return ollama_client.decide(sys_p, usr_p)
    return claude_client.decide(signal, context)


def ml_filter_build(symbols: list) -> tuple:
    """
    Her hisse için günlük ML tahminlerini önceden hesaplar.
    Returns: (ml_client, daily_preds) where
        daily_preds[sym][date] = {"signal":..., "prob_al":...}
    """
    from ai_engine.ml_client import MLClient
    client = MLClient(variant="shap_1g")
    if not client.available:
        print("  [ML] Model yüklenemedi — ML filtre devre dışı")
        return None, {}

    print("  ML tahminleri hesaplanıyor (vektörize)...")
    daily_preds: dict[str, dict] = {}
    for sym in symbols:
        df_1d = load_symbol(sym, "1d")
        if df_1d.empty or len(df_1d) < 60:
            print(f"    {sym:<14} 1d veri yok — atlandı")
            continue
        preds = client.predict_all(sym, df_1d)
        daily_preds[sym] = preds
        al_count = sum(1 for v in preds.values() if v["signal"] == 2)
        print(f"    {sym:<14} {len(preds)} gün  →  AL: {al_count} (%{al_count/len(preds)*100:.0f})")
    return client, daily_preds


def close_positions(broker, data: dict, ts, trade_log: list, label: str = "eod"):
    """Açık tüm pozisyonları verilen timestamp'teki fiyattan kapat."""
    for sym, df in data.items():
        pos = repo.get_open_position(sym)
        if not pos:
            continue
        if ts in df.index:
            price = float(df.loc[ts, "Close"])
        else:
            price = float(df["Close"].iloc[-1])
        pnl_pct = (price - pos.avg_cost) / pos.avg_cost
        broker.sell(sym, pos.quantity, price, source=label)
        trade_log.append((ts.strftime("%d/%m %H:%M"), sym.replace(".IS", ""),
                          f"SAT({label.upper()})", price, f"{pnl_pct:+.1%}"))


def run(interval: str = "1m", engine: str = "rule", exit_mode: str = "eod",
        symbols: list = None, min_conf: float = 0.70, no_buy_after: str | None = None,
        tp_pct: float | None = None, sl_pct: float | None = None,
        capital: float | None = None):

    symbols = symbols or BIST30_SYMBOLS[:10]
    check_every = CHECK_EVERY_MAP.get(interval, 15)
    round_trip_cost = config.commission_rate * 2   # her iki bacakta da komisyon
    no_buy_after_time = parse_hhmm(no_buy_after)
    take_profit_pct = config.take_profit_pct if tp_pct is None else tp_pct
    stop_loss_pct = config.stop_loss_pct if sl_pct is None else sl_pct

    engine_label = {
        "rule":      "Kural Tabanlı",
        "ollama":    f"Kural + Ollama ({config.ollama_model})",
        "claude":    "Kural + Claude AI",
        "ml":        "Kural + ML (SHAP-1g XGBoost)",
        "ml-daily":  "ML Günlük Swing (SHAP-1g XGBoost)",
    }
    exit_label = {
        "eod":       "Gün sonu zorunlu çıkış (son mum)",
        "overnight": "Geceye taşı (açık gap dahil)",
        "signal":    "Sadece sinyal/stop çıkışı",
    }

    print("=" * 66)
    print(f"  BIST Algo Backtest  |  {interval}  |  Güven ≥ {min_conf:.0%}")
    print("=" * 66)

    # İzole in-memory DB — canlı veriyi kirletmez
    db.init(":memory:", pragmas={"journal_mode": "wal"})
    db.connect(reuse_if_open=True)
    db.create_tables([Trade, Position, AIDecision, PortfolioSnapshot, Watchlist, BotState], safe=True)

    start_value = capital if capital is not None else config.initial_capital
    if capital is not None:
        config.initial_capital = capital   # position_size ve risk_manager bunu kullanır
    broker = PaperTrader.__new__(PaperTrader)
    broker._cash        = start_value
    broker._start_value = start_value

    print(f"  Sermaye    : {start_value:,.0f} TL")
    print(f"  Hisseler   : {', '.join(s.replace('.IS','') for s in symbols)}")
    print(f"  Motor      : {engine_label.get(engine, engine)}")
    print(f"  Çıkış modu : {exit_label.get(exit_mode, exit_mode)}")
    print(f"  Kontrol    : Her {check_every} mumda bir  |  Cooldown: {COOLDOWN_CHECKS} kontrol aralığı")
    print(f"  Risk       : TP %{take_profit_pct*100:.2f}  |  SL %{stop_loss_pct*100:.2f}")
    if no_buy_after_time:
        print(f"  Giriş      : {no_buy_after_time.strftime('%H:%M')} sonrası yeni alım yok")
    print()

    # Veri yükle + indikatör hesapla
    print("Veriler yükleniyor...")
    data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        df = load_symbol(sym, interval)
        if df.empty or len(df) < 50:
            print(f"  {sym:<14} diskde yok — önce: python -m data_feed.downloader")
            continue
        data[sym] = compute_all(df)
        dr = f"{df.index[0].strftime('%d/%m %H:%M')} – {df.index[-1].strftime('%d/%m %H:%M')}"
        print(f"  {sym:<14} {len(df):>6} mum  {dr}")

    if not data:
        print("\nHiç veri yok!")
        return

    # ML filtre — günlük tahminleri önceden hesapla
    ml_preds: dict[str, dict] = {}
    ml_prob_threshold = 0.30   # AL olasılığı bu eşiğin üstündeyse izin ver
    if engine in ("ml", "ml-daily"):
        _, ml_preds = ml_filter_build(list(data.keys()))

    print()

    # Gün → son timestamp eşlemesi (EOD çıkışı için)
    all_timestamps = sorted({ts for df in data.values() for ts in df.index})
    day_last_bar: dict[datetime.date, pd.Timestamp] = {}
    day_first_bar: dict[datetime.date, pd.Timestamp] = {}
    for ts in all_timestamps:
        day_last_bar[ts.date()] = ts   # son yazılan = o günün son barı
        if ts.date() not in day_first_bar:
            day_first_bar[ts.date()] = ts  # ilk yazılan = o günün ilk barı

    # ml-daily: gün bazında sıralı işlem günleri (önceki gün lookup için)
    sorted_trading_days = sorted(day_first_bar.keys())
    prev_trading_day: dict[datetime.date, datetime.date] = {}
    for i, d in enumerate(sorted_trading_days):
        if i > 0:
            prev_trading_day[d] = sorted_trading_days[i - 1]

    trade_log   = []
    mum_counter = {sym: 0 for sym in data}
    cooldown    = {sym: 0 for sym in data}   # kalan kontrol aralığı sayısı

    for ts in all_timestamps:
        is_last_bar_of_day = (ts == day_last_bar.get(ts.date()))

        # EOD zorunlu çıkış — günün GERÇEK son barında
        if exit_mode == "eod" and is_last_bar_of_day:
            close_positions(broker, data, ts, trade_log, label="eod")
            continue   # bu barı sinyal tarama olarak işleme

        for sym, df in data.items():
            if ts not in df.index:
                continue

            idx = df.index.get_loc(ts)
            if idx < 30:
                continue

            # Her CHECK_EVERY mumda bir kontrol
            mum_counter[sym] = (mum_counter[sym] + 1) % check_every
            if mum_counter[sym] != 0:
                continue

            # Cooldown: satıştan sonra N kontrol aralığı bekle
            if cooldown[sym] > 0:
                cooldown[sym] -= 1
                continue

            ind = latest_values(df.iloc[:idx + 1])
            if not ind or not ind.get("close"):
                continue

            price = ind["close"]
            pos   = repo.get_open_position(sym)

            # Stop-loss / take-profit
            if pos:
                pnl_pct = (price - pos.avg_cost) / pos.avg_cost
                if pnl_pct <= -stop_loss_pct:
                    broker.sell(sym, pos.quantity, price, source="sl")
                    trade_log.append((ts.strftime("%d/%m %H:%M"), sym.replace(".IS",""),
                                      "SAT(SL)", price, f"{pnl_pct:+.1%}"))
                    cooldown[sym] = COOLDOWN_CHECKS
                    continue
                elif pnl_pct >= take_profit_pct:
                    broker.sell(sym, pos.quantity, price, source="tp")
                    trade_log.append((ts.strftime("%d/%m %H:%M"), sym.replace(".IS",""),
                                      "SAT(TP)", price, f"{pnl_pct:+.1%}"))
                    cooldown[sym] = COOLDOWN_CHECKS
                    continue

            # ── ML-DAILY: kural yok, sadece önceki günün ML sinyali ──────────
            if engine == "ml-daily":
                if not pos:
                    # Sadece günün ilk barında (10:30) giriş değerlendir
                    if ts != day_first_bar.get(ts.date()):
                        continue
                    prev_day = prev_trading_day.get(ts.date())
                    if prev_day is None:
                        continue
                    ml_day = ml_preds.get(sym, {}).get(prev_day, {})
                    if ml_day.get("signal", 1) != 2:           # önceki gün AL değilse geç
                        continue
                    if ml_day.get("prob_al", 0) < ml_prob_threshold:
                        continue
                    qty = position_size(price, 0.15, broker.get_cash())
                    if qty > 0:
                        ok, _ = can_open_position(sym, qty, price, broker)
                        if ok:
                            broker.buy(sym, qty, price, source="auto")
                            trade_log.append((ts.strftime("%d/%m %H:%M"), sym.replace(".IS",""),
                                              "AL", price, f"x{qty}"))
                            p = ml_day.get("prob_al", 0)
                            print(f"  {ts.strftime('%d/%m %H:%M')}  {sym.replace('.IS',''):<8}  "
                                  f"AL   {price:>8.2f} TL  ML:{p:.0%}  (önceki gün AL sinyali)")
                continue   # ml-daily: kural tabanlı SAT kontrolü yok

            # ── KURAL TABANLI (rule / ml / ollama / claude) ────────────────
            signal = evaluate(sym, ind)
            if signal.candidate == "NONE":
                continue

            # Karar motoru
            decision = rule_decision(signal)
            if engine in ("ollama", "claude") and decision.confidence >= 0.65:
                context = {
                    "has_position":  pos is not None,
                    "quantity":      pos.quantity if pos else 0,
                    "avg_cost":      pos.avg_cost if pos else 0,
                    "cash_available": broker.get_cash(),
                    "total_value":   broker.get_balance().total_value,
                    "daily_pnl":     broker.get_balance().daily_pnl,
                    "daily_pnl_pct": broker.get_balance().daily_pnl_pct,
                }
                decision = ai_approve(signal, context, engine)

            if decision.confidence < min_conf:
                continue

            if decision.action == "BUY" and not pos:
                if no_buy_after_time and ts.time() >= no_buy_after_time:
                    continue
                # ML filtre: model SAT diyorsa veya AL olasılığı düşükse atla
                if engine == "ml" and ml_preds.get(sym):
                    ml_day = ml_preds[sym].get(ts.date(), {})
                    if ml_day.get("signal", 1) == 0:
                        continue
                    if ml_day.get("prob_al", 0) < ml_prob_threshold:
                        continue
                # Minimum hareket filtresi: beklenen TP en az komisyonun 2 katı olmalı
                if take_profit_pct < round_trip_cost * 2:
                    continue
                qty = position_size(price, 0.15, broker.get_cash())
                if qty > 0:
                    ok, _ = can_open_position(sym, qty, price, broker)
                    if ok:
                        broker.buy(sym, qty, price, source="auto")
                        trade_log.append((ts.strftime("%d/%m %H:%M"), sym.replace(".IS",""),
                                          "AL", price, f"x{qty}"))
                        rsi_s = f"{ind['rsi']:.0f}" if ind.get("rsi") else "-"
                        mc    = ind.get("macd_cross") or "-"
                        strat = signal.strategy[:5].upper()
                        ml_tag = ""
                        if engine == "ml" and ml_preds.get(sym):
                            p = ml_preds[sym].get(ts.date(), {}).get("prob_al", 0)
                            ml_tag = f"  ML:{p:.0%}"
                        print(f"  {ts.strftime('%d/%m %H:%M')}  {sym.replace('.IS',''):<8}  "
                              f"AL   {price:>8.2f} TL  RSI:{rsi_s}  MACD:{mc}  [{strat}] Skor:{signal.score}/4{ml_tag}")

            elif decision.action == "SELL" and pos:
                pnl_pct = (price - pos.avg_cost) / pos.avg_cost
                broker.sell(sym, pos.quantity, price, source="auto")
                trade_log.append((ts.strftime("%d/%m %H:%M"), sym.replace(".IS",""),
                                  "SAT", price, f"{pnl_pct:+.1%}"))
                cooldown[sym] = COOLDOWN_CHECKS
                rsi_s = f"{ind['rsi']:.0f}" if ind.get("rsi") else "-"
                print(f"  {ts.strftime('%d/%m %H:%M')}  {sym.replace('.IS',''):<8}  "
                      f"SAT  {price:>8.2f} TL  RSI:{rsi_s}  P&L:{pnl_pct:+.1%}")

    # Bitiş kapanışı (overnight veya signal modunda kalan pozisyonlar)
    if exit_mode != "eod":
        last_ts = all_timestamps[-1]
        close_positions(broker, data, last_ts, trade_log, label="final")

    # --- Sonuçlar ---
    final  = broker.get_balance()
    trades = repo.get_trades(limit=5000)
    buys   = [t for t in trades if t.side == "BUY"]
    sells  = [t for t in trades if t.side == "SELL"]
    commis = sum(t.commission for t in trades)
    net_pnl = final.total_value - start_value
    net_pct = net_pnl / start_value * 100

    closed = [t for t in trade_log if t[2].startswith("SAT")]
    winning = sum(1 for t in closed if "+" in t[4])
    losing  = sum(1 for t in closed if "-" in t[4])

    print()
    print("=" * 66)
    print("  SONUÇLAR")
    print("=" * 66)
    print(f"  Başlangıç  : {start_value:>10,.0f} TL")
    print(f"  Bitiş      : {final.total_value:>10,.0f} TL")
    print(f"  Net K/Z    : {net_pnl:>+10,.0f} TL  ({net_pct:+.2f}%)")
    print(f"  Komisyon   : {commis:>10,.1f} TL  (round-trip: %{round_trip_cost*100:.2f})")
    print(f"  İşlem      : {len(buys)} alım  |  {len(sells)} satım")
    if winning + losing > 0:
        wr = winning / (winning + losing) * 100
        print(f"  Kazanan/K  : {winning} / {losing}  (Win rate: %{wr:.0f})")
    print()

    if trade_log:
        print(f"  {'Zaman':<14} {'Hisse':<8} {'İşlem':<12} {'Fiyat':>9}  {'Not'}")
        print("  " + "-" * 54)
        for row in trade_log:
            print(f"  {row[0]:<14} {row[1]:<8} {row[2]:<12} {row[3]:>9.2f}  {row[4]}")
    print()
    sonuc = "KAR ✓" if net_pnl > 0 else "ZARAR ✗"
    print(f"  Sonuç: {sonuc}  ({interval} / {exit_mode} / {net_pct:+.1f}%)")
    print("=" * 66)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval",   default="1m",  choices=["1m", "5m", "15m", "1h"])
    parser.add_argument("--engine",     default="rule", choices=["rule", "ollama", "claude", "ml", "ml-daily"])
    parser.add_argument("--exit-mode",  default="eod", choices=["eod", "overnight", "signal"],
                        dest="exit_mode")
    parser.add_argument("--symbols",    nargs="+", default=None)
    parser.add_argument("--min-conf",   type=float, default=0.70, dest="min_conf")
    parser.add_argument("--no-buy-after", default=None,
                        help="Bu saatten sonra yeni pozisyon açma, örn: 14:00")
    parser.add_argument("--tp-pct", type=float, default=None,
                        help="Take-profit oranı, örn: 0.015")
    parser.add_argument("--sl-pct", type=float, default=None,
                        help="Stop-loss oranı, örn: 0.02")
    parser.add_argument("--capital", type=float, default=None,
                        help="Başlangıç sermayesi TL, örn: 100000")
    args = parser.parse_args()

    run(
        interval=args.interval,
        engine=args.engine,
        exit_mode=args.exit_mode,
        symbols=args.symbols,
        min_conf=args.min_conf,
        no_buy_after=args.no_buy_after,
        tp_pct=args.tp_pct,
        sl_pct=args.sl_pct,
        capital=args.capital,
    )
