"""
main.py — ICS 指揮部後端 API（C0 重構版）

啟動方式：
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

版本：command-v2.0.0（C0 架構重構）
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from core.config import STATIC_DIR, APP_VERSION
from core.database import init_db
from auth.middleware import auth_middleware
from repositories.account_repo import ensure_default_admin
from repositories.config_repo import ensure_default_admin_pin

# ── Routers ───────────────────────────────────────────────────────────────────
from routers import (
    auth, snapshots, events, decisions, admin,
    pi_push, sync, manual, dashboard,
    config_router, map, exercises, ttx, ai, tak,
)

# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_default_admin()
    ensure_default_admin_pin()
    yield


app = FastAPI(
    title="ICS 指揮部 API",
    version=APP_VERSION,
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(auth_middleware)

# ── 靜態檔案 ──────────────────────────────────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── 路由 ──────────────────────────────────────────────────────────────────────
for router in (
    auth.router, snapshots.router, events.router, decisions.router,
    admin.router, pi_push.router, sync.router, manual.router,
    dashboard.router, config_router.router, map.router,
    exercises.router, ttx.router, ai.router, tak.router,
):
    app.include_router(router)


# ── 首頁 ──────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index():
    return f"""<html><head><meta charset="UTF-8"><title>ICS 指揮部</title></head>
    <body style="font-family:monospace;padding:20px;background:#0a0e1a;color:#9ab0c8">
    <h2 style="color:#fff">ICS 指揮部 command-{APP_VERSION}</h2>
    <p><a href="/static/commander_dashboard.html" style="color:#f0883e;font-weight:bold">▶ 儀表板</a></p>
    <p><a href="/docs" style="color:#90b8e8">/docs — Swagger UI</a></p>
    <p><a href="/api/health" style="color:#90b8e8">/api/health</a></p>
    </body></html>"""


