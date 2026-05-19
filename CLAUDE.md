# BIST Algo Trading Bot — CLAUDE.md

## Proje Özeti

Borsa İstanbul (BIST) üzerinde çalışan, Claude AI destekli intraday al-sat botu.
Şu an **paper trading** (simülasyon) modunda. Gerçek emir gönderme altyapısı henüz AlgoLab'a bağlı değil.

- Sermaye: 10.000 TL (sanal)
- Piyasa: BIST-30 hisseleri
- Veri kaynağı: yfinance (Yahoo Finance)
- AI karar motoru: Claude claude-sonnet-4-6 → Ollama fallback
- Veritabanı: SQLite (`data/trading.db`, peewee ORM)

---

## Mimariye Genel Bakış

```
main.py          → Bot başlatma noktası
backtest.py      → Geçmiş veri ile strateji testi
web/app.py       → FastAPI dashboard (port 8000)

core/
  scheduler.py   → Ana döngü (60s aralık), tüm iş akışını yönetir
  market_hours.py→ BIST piyasa saati kontrolü (10:00–17:15)
  bot_state.py   → RUNNING / PAUSED / STOPPED durumu

data_feed/
  price_fetcher.py → yfinance üzerinden OHLCV + anlık fiyat
  data_cache.py    → Tekrarlayan API çağrısını önler
  bist30_symbols.py→ BIST-30 sembol listesi (.IS uzantılı)

analysis/
  indicators.py       → RSI-14, MACD 12/26/9, EMA-9/21, Hacim-MA20
  signal_generator.py → Teknik göstergeleri AL/SAT/NONE'a çevirir

ai_engine/
  claude_client.py    → Anthropic API çağrısı, Ollama fallback
  ollama_client.py    → Yerel Ollama (glm-4.7:cloud varsayılan)
  prompt_builder.py   → Sinyal + portföy bağlamından prompt oluşturur
  decision_parser.py  → AI yanıtını TradingDecision nesnesine parse eder

risk/
  risk_manager.py       → Stop-loss (%5), take-profit (%3), günlük kayıp limiti (%3)
  portfolio_calculator.py → Pozisyon büyüklüğü hesabı, portföy bağlamı

trading/
  paper_trader.py   → Sanal broker: buy/sell/balance, komisyon hesabı
  broker_interface.py → Gerçek AlgoLab bağlantısı için hazır arayüz

storage/
  models.py        → Trade, Position, Decision, Snapshot, Symbol tabloları
  repositories.py  → Tüm DB erişimi buradan; doğrudan ORM kullanma
  database.py      → init_db() — uygulama başlarken çağrılır

web/routers/
  dashboard.py, control.py, positions.py,
  trades.py, ai_log.py, manual.py, watchlist.py
```

---

## Ortam Kurulumu

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env içine ANTHROPIC_API_KEY ekle
```

`.env` zorunlu alanları:
```
ANTHROPIC_API_KEY=sk-ant-...
TRADING_MODE=paper          # paper | live (live henüz hazır değil)
```

---

## Çalıştırma

```bash
# Trading botu
python main.py

# Web dashboard (http://localhost:8000)
uvicorn web.app:app --reload --log-config=data/web.log

# Backtest (son 55 gün, ilk 10 BIST-30 hissesi)
python backtest.py
```

---

## Risk Parametreleri (`config.py`)

| Parametre | Değer | Açıklama |
|-----------|-------|----------|
| `max_position_pct` | %20 | Tek pozisyon max 2.000 TL |
| `stop_loss_pct` | %5 | Otomatik zarar kes |
| `take_profit_pct` | %3 | Otomatik kâr al |
| `max_daily_loss_pct` | %3 | Günlük 300 TL → bot durur |
| `max_open_positions` | 5 | Aynı anda max açık pozisyon |
| `commission_rate` | %0.15 | Alış + satış toplam komisyon |

---

## Al/Sat Mantığı

`core/scheduler.py → _process_symbol()`:

1. `price_fetcher` → OHLCV çek
2. `indicators.compute_all()` → RSI, MACD, EMA, Hacim hesapla
3. `signal_generator.evaluate()` → AL/SAT/NONE sinyali üret
4. Sinyal NONE ise → Claude'a gönderilmez, devam
5. `claude_client.decide()` → BUY / SELL / HOLD kararı + güven skoru
6. Güven ≥ 0.60 ise `risk_manager.can_open_position()` kontrolü
7. Geçerse `broker.buy()` / `broker.sell()`

Al sinyali koşulları (3/4 sağlanmalı):
- RSI < 35
- MACD yukarı kesişim
- Hacim 20 günlük ortalamanın 1.5x üzeri
- Fiyat EMA-9 üzerinde

---

## AI Motoru

`claude_client.decide()` önce Anthropic API'yi dener:
- API key geçersiz veya kredi yetersizse → `_anthropic_available = False` set edilir
- Bir kez başarısız olursa aynı session boyunca Ollama'ya geçer (tekrar denemez)
- Ollama URL: `OLLAMA_BASE_URL` env değişkeni (varsayılan `http://localhost:11434`)

Prompt cache aktif: system prompt `cache_control: ephemeral` ile gönderilir.

---

## Önemli Kurallar

- **DB'ye doğrudan ORM erişimi yapma** — tüm sorgular `storage/repositories.py` üzerinden
- **Config değerlerini hardcode etme** — `from config import config` kullan
- **Gün sonu (17:15) tüm pozisyonlar zorunlu kapanır** — `market_hours.is_force_close_time()`
- **T+2 takas** — satıştan gelen nakit 2 iş günü sonra serbest; PaperTrader bunu takip etmiyor (gerçek modda dikkat)
- **AlgoLab entegrasyonu** — `trading/broker_interface.py` hazır ama bağlanmamış; `TRADING_MODE=live` ayarlanınca devreye girmeli

---

## Semboller

`data_feed/bist30_symbols.py` — Yahoo Finance formatı (örn. `THYAO.IS`).
Scheduler varsayılan olarak `BIST30_SYMBOLS[:5]` kullanır; DB'de `active_symbols` tablosu doluysa oradan çeker.

---

## Veri ve Loglar

```
data/bot.log      → Bot runtime logu
data/web.log      → FastAPI/uvicorn logu
data/trading.db   → SQLite (trades, positions, decisions, snapshots)
data/backtest.log → Backtest çıktısı
```
