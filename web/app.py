from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from storage.database import init_db
from web.routers import dashboard, control, positions, trades, ai_log, manual, watchlist

app = FastAPI(title="BIST Algo Dashboard")
app.mount("/static", StaticFiles(directory="web/static"), name="static")

init_db()

app.include_router(dashboard.router)
app.include_router(control.router)
app.include_router(positions.router)
app.include_router(trades.router)
app.include_router(ai_log.router)
app.include_router(manual.router)
app.include_router(watchlist.router)
