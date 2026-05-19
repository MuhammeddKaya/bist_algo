import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # API Keys
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    algolab_api_key: str = field(default_factory=lambda: os.getenv("ALGOLAB_API_KEY", ""))
    algolab_username: str = field(default_factory=lambda: os.getenv("ALGOLAB_USERNAME", ""))
    algolab_password: str = field(default_factory=lambda: os.getenv("ALGOLAB_PASSWORD", ""))

    # Mod
    trading_mode: str = field(default_factory=lambda: os.getenv("TRADING_MODE", "paper"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Sermaye
    initial_capital: float = 10_000.0

    # Risk parametreleri
    max_position_pct: float = 0.20       # Sermayenin max %20'si tek pozisyona
    stop_loss_pct: float = 0.05          # %5 stop-loss
    take_profit_pct: float = 0.03        # %3 take-profit
    max_daily_loss_pct: float = 0.03     # Günlük max %3 kayıp
    commission_rate: float = 0.0015      # %0.15 alış VEYA satış başına; round-trip %0.30
    max_open_positions: int = 5

    # Zamanlama (Türkiye saati, UTC+3)
    trading_start: str = "10:00"
    trading_end: str = "17:00"
    force_close_time: str = "17:15"
    scan_interval_seconds: int = 60
    snapshot_interval_minutes: int = 5

    # Veri
    data_interval: str = "5m"
    data_period: str = "1d"

    # Claude
    claude_model: str = "claude-sonnet-4-6"

    # Ollama fallback
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "glm-4.7:cloud"))

    # DB
    db_path: str = "data/trading.db"


config = Config()
