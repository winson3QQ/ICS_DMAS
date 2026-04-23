"""
auth/service.py — Session 管理與 PIN 驗證
"""

import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, Request

from core.config import SESSION_TIMEOUT

# ── 在記憶體中維護 session dict ──────────────────────────────────────────────
# {token: {username, role, last_active, ...}}
_sessions: dict[str, dict] = {}


def create_session(account: dict) -> str:
    """建立新 session，回傳 token"""
    token = str(uuid.uuid4())
    _sessions[token] = {
        **account,
        "last_active": datetime.now(timezone.utc).timestamp(),
    }
    return token


def validate_session(request: Request) -> dict:
    """驗證 X-Session-Token，回傳 session dict 或拋 401"""
    token = request.headers.get("X-Session-Token")
    if not token or token not in _sessions:
        raise HTTPException(401, "未登入或 session 已過期")
    sess = _sessions[token]
    now = datetime.now(timezone.utc).timestamp()
    if now - sess["last_active"] > SESSION_TIMEOUT:
        _sessions.pop(token, None)
        raise HTTPException(401, "閒置超時，請重新登入")
    sess["last_active"] = now
    return sess


def get_session(token: str) -> dict | None:
    """取得 session（不刷新 last_active），回傳 None 表示不存在或過期"""
    sess = _sessions.get(token)
    if not sess:
        return None
    now = datetime.now(timezone.utc).timestamp()
    if now - sess["last_active"] > SESSION_TIMEOUT:
        _sessions.pop(token, None)
        return None
    return sess


def destroy_session(token: str) -> dict | None:
    """刪除 session，回傳被刪除的 session dict（若存在）"""
    return _sessions.pop(token, None)


def session_remaining(token: str) -> int:
    """回傳 session 剩餘秒數（不存在或過期回傳 0）"""
    sess = _sessions.get(token)
    if not sess:
        return 0
    now = datetime.now(timezone.utc).timestamp()
    elapsed = now - sess["last_active"]
    return max(0, int(SESSION_TIMEOUT - elapsed))
