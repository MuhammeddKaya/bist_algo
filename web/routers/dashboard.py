from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from storage import repositories as repo
from core import bot_state, market_hours

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    snapshot = repo.get_latest_snapshot()
    positions = repo.get_all_open_positions()
    decisions = repo.get_decisions(limit=5)
    snapshots = repo.get_snapshots(days=7)
    state = repo.get_bot_state()

    pnl_labels = [s.timestamp.strftime("%d/%m %H:%M") for s in snapshots]
    pnl_values = [round(s.total_value, 2) for s in snapshots]

    return templates.TemplateResponse(request, "dashboard.html", {
        "snapshot": snapshot,
        "positions": positions,
        "decisions": decisions,
        "bot_status": state.status if state else "STOPPED",
        "bot_mode": state.mode if state else "paper",
        "market_open": market_hours.is_market_open(),
        "pnl_labels": pnl_labels,
        "pnl_values": pnl_values,
    })


@router.get("/api/status")
def api_status():
    snapshot = repo.get_latest_snapshot()
    positions = repo.get_all_open_positions()
    state = repo.get_bot_state()
    return {
        "bot_status": state.status if state else "STOPPED",
        "cash": round(snapshot.cash, 2) if snapshot else 0,
        "total_value": round(snapshot.total_value, 2) if snapshot else 0,
        "daily_pnl": round(snapshot.daily_pnl, 2) if snapshot else 0,
        "daily_pnl_pct": round(snapshot.daily_pnl_pct, 2) if snapshot else 0,
        "open_positions": len(positions),
        "market_open": market_hours.is_market_open(),
    }
