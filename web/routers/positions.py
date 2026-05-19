from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from storage import repositories as repo
from data_feed.price_fetcher import get_current_price
from trading.paper_trader import PaperTrader
from storage.database import init_db

router = APIRouter(prefix="/positions")
templates = Jinja2Templates(directory="web/templates")


@router.get("", response_class=HTMLResponse)
def positions_page(request: Request):
    positions = repo.get_all_open_positions()
    enriched = []
    for pos in positions:
        price = get_current_price(pos.symbol)
        pnl = (price - pos.avg_cost) * pos.quantity if price else 0
        pnl_pct = ((price - pos.avg_cost) / pos.avg_cost * 100) if price and pos.avg_cost else 0
        stop_price = pos.avg_cost * 0.95
        target_price = pos.avg_cost * 1.03
        enriched.append({
            "symbol": pos.symbol,
            "quantity": pos.quantity,
            "avg_cost": pos.avg_cost,
            "current_price": price,
            "value": price * pos.quantity if price else 0,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "stop_price": stop_price,
            "target_price": target_price,
        })
    return templates.TemplateResponse(request, "positions.html", {"positions": enriched})


@router.post("/sell/{symbol}")
def manual_sell(symbol: str):
    init_db()
    broker = PaperTrader()
    broker.sync_cash()
    pos = repo.get_open_position(symbol)
    if pos:
        price = get_current_price(symbol)
        if price:
            broker.sell(symbol, pos.quantity, price, source="manual")
    return RedirectResponse("/positions", status_code=303)
