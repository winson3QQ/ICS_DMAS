"""
auth/middleware.py — 全域 HTTP 認證中介層
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from core.config import AUTH_EXEMPT_EXACT, AUTH_EXEMPT_PREFIXES
from .service import check_and_touch


async def auth_middleware(request: Request, call_next):
    path   = request.url.path
    method = request.method

    # 精確豁免
    if (method, path) in AUTH_EXEMPT_EXACT:
        return await call_next(request)

    # 前綴豁免（Swagger、靜態、tile server）
    if any(path.startswith(p) for p in AUTH_EXEMPT_PREFIXES):
        return await call_next(request)

    # 首頁
    if path == "/":
        return await call_next(request)

    # GET /api/snapshots/<node_type> — Pi 讀取最新快照，無需 session
    if method == "GET" and path.startswith("/api/snapshots/"):
        return await call_next(request)

    # /api/admin/* — X-Admin-PIN 由各 router handler 自行驗證
    if path.startswith("/api/admin/"):
        return await call_next(request)

    # /api/pi-push/* — Bearer token 由各 router handler 自行驗證
    if path.startswith("/api/pi-push/"):
        return await call_next(request)

    # POST /api/snapshots — 機對機推送，無需 session
    if method == "POST" and path == "/api/snapshots":
        return await call_next(request)

    # POST /api/sync/push — 網路恢復同步，無需 session
    if method == "POST" and path == "/api/sync/push":
        return await call_next(request)

    # GET /api/health, GET /api/status
    if path in ("/api/health", "/api/status"):
        return await call_next(request)

    # 其餘 /api/ 端點需要有效 session
    if path.startswith("/api/"):
        token = request.headers.get("X-Session-Token")
        if not token:
            return JSONResponse({"detail": "未登入或 session 已過期"}, status_code=401)
        sess = check_and_touch(token)
        if sess is None:
            return JSONResponse({"detail": "未登入或 session 已過期"}, status_code=401)
        # 存入 request.state，供 validate_session() 直接讀取，避免重複 DB 查詢
        request.state.session = sess

    return await call_next(request)
