from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from storage import repositories as repo

router = APIRouter(prefix="/watchlist")
templates = Jinja2Templates(directory="web/templates")


@router.get("", response_class=HTMLResponse)
def watchlist_page(request: Request):
    items = repo.get_watchlist()
    return templates.TemplateResponse(request, "watchlist.html", {"items": items})


@router.post("/add")
def add_symbol(symbol: str = Form(...)):
    full = symbol.upper().strip()
    if not full.endswith(".IS"):
        full += ".IS"
    repo.add_to_watchlist(full, added_by="manual")
    return RedirectResponse("/watchlist", status_code=303)


@router.post("/remove/{symbol}")
def remove_symbol(symbol: str):
    repo.remove_from_watchlist(symbol)
    return RedirectResponse("/watchlist", status_code=303)
