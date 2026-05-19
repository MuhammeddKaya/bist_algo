from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from storage import repositories as repo

router = APIRouter(prefix="/ai-decisions")
templates = Jinja2Templates(directory="web/templates")


@router.get("", response_class=HTMLResponse)
def ai_decisions_page(request: Request, action: str = Query(default=None)):
    decisions = repo.get_decisions(limit=100, action_filter=action)
    return templates.TemplateResponse(request, "ai_decisions.html", {
        "decisions": decisions,
        "action_filter": action,
    })
