from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from storage import repositories as repo
from core import bot_state

router = APIRouter(prefix="/bot")


@router.post("/start")
def start():
    repo.set_bot_status("RUNNING")
    return RedirectResponse("/", status_code=303)


@router.post("/stop")
def stop():
    repo.set_bot_status("STOPPED")
    return RedirectResponse("/", status_code=303)


@router.post("/pause")
def pause():
    repo.set_bot_status("PAUSED")
    return RedirectResponse("/", status_code=303)
