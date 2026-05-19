from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from storage import repositories as repo

router = APIRouter(prefix="/trades")
templates = Jinja2Templates(directory="web/templates")


@router.get("", response_class=HTMLResponse)
def trades_page(request: Request):
    trades = repo.get_trades(limit=100)
    return templates.TemplateResponse(request, "trades.html", {"trades": trades})
