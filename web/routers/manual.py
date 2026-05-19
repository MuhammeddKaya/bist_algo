from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from storage import repositories as repo
from data_feed.price_fetcher import get_current_price
from data_feed.bist30_symbols import BIST30_SYMBOLS
from trading.paper_trader import PaperTrader
from storage.database import init_db

router = APIRouter(prefix="/manual")
templates = Jinja2Templates(directory="web/templates")


@router.get("", response_class=HTMLResponse)
def manual_page(request: Request):
    watchlist = repo.get_active_symbols() or [s.replace(".IS", "") for s in BIST30_SYMBOLS]
    return templates.TemplateResponse(request, "manual_trade.html", {
        "symbols": watchlist,
    })


@router.post("/order")
def place_order(
    symbol: str = Form(...),
    side: str = Form(...),
    quantity: int = Form(...),
):
    full_symbol = symbol if symbol.endswith(".IS") else symbol + ".IS"
    init_db()
    broker = PaperTrader()
    broker.sync_cash()
    price = get_current_price(full_symbol)

    if price and price > 0:
        if side == "BUY":
            broker.buy(full_symbol, quantity, price, source="manual")
        elif side == "SELL":
            pos = repo.get_open_position(full_symbol)
            qty = min(quantity, pos.quantity) if pos else 0
            if qty > 0:
                broker.sell(full_symbol, qty, price, source="manual")

    return RedirectResponse("/positions", status_code=303)
