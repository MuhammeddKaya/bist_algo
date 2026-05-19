import logging
import sys
from storage.database import init_db
from trading.paper_trader import PaperTrader
from core.scheduler import start_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/bot.log"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    logger.info("BIST Algo Bot başlatılıyor...")
    init_db()

    broker = PaperTrader()
    logger.info(f"Paper Trader hazır | Bakiye: {broker.get_cash():.0f} TL")

    start_loop(broker)


if __name__ == "__main__":
    main()
