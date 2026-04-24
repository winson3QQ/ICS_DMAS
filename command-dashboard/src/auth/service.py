"""
auth/service.py — Session 管理與 PIN 驗證（SQLite 持久化）

設計原則：
- Session 寫入 SQLite，server 重啟後仍有效
- Middleware 驗證後將 session dict 存入 request.state.session
- validate_session() 優先讀 request.state，避免重複 DB 查詢
- check_and_touch() 為 middleware 專用：原子讀取 + 更新 last_active
"""

import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, Request

from core.config import SESSION_TIMEOUT
from core.database import get_conn


# ── 時間工具 ─────────────────────────────────────────────────────────────────

def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _iso_to_ts(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


# ── 公開 API ─────────────────────────────────────────────────────────────────

def create_session(account: dict) -> str:
    """建立新 session，寫入 DB，回傳 token"""
    token = str(uuid.uuid4())
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO sessions (token, username, role, display_name, last_active)
               VALUES (?, ?, ?, ?, ?)""",
            (token,
             account["username"],
             account["role"],
             account.get("display_name"),
             _now_iso())
        )
        conn.commit()
    finally:
        conn.close()
    return token


def validate_session(request: Request) -> dict:
    """驗證 X-Session-Token，回傳 session dict 或拋 401

    優先從 request.state.session 讀取（middleware 已驗證過），
    避免重複查詢 DB。
    """
    if hasattr(request.state, "session") and request.state.session:
        return request.state.session
    # fallback：直接查 DB（middleware 未覆蓋的路徑）
    token = request.headers.get("X-Session-Token")
    if not token:
        raise HTTPException(401, "未登入或 session 已過期")
    sess = check_and_touch(token)
    if sess is None:
        raise HTTPException(401, "未登入或 session 已過期")
    return sess


def check_and_touch(token: str) -> dict | None:
    """原子讀取 + 更新 last_active；供 middleware 使用。
    回傳 session dict，或 None（不存在 / 已過期）。
    """
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            return None
        row = dict(row)
        now = _now_ts()
        if now - _iso_to_ts(row["last_active"]) > SESSION_TIMEOUT:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        conn.execute(
            "UPDATE sessions SET last_active = ? WHERE token = ?",
            (_now_iso(), token)
        )
        conn.commit()
        return row
    finally:
        conn.close()


def get_session(token: str) -> dict | None:
    """讀取 session（不刷新 last_active），回傳 None 表示不存在或過期"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            return None
        row = dict(row)
        if _now_ts() - _iso_to_ts(row["last_active"]) > SESSION_TIMEOUT:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        return row
    finally:
        conn.close()


def destroy_session(token: str) -> dict | None:
    """刪除 session，回傳被刪除的 session dict（若存在）"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return dict(row)
        return None
    finally:
        conn.close()


def session_remaining(token: str) -> int:
    """回傳 session 剩餘秒數（不存在或過期回傳 0）"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT last_active FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            return 0
        elapsed = _now_ts() - _iso_to_ts(row["last_active"])
        return max(0, int(SESSION_TIMEOUT - elapsed))
    finally:
        conn.close()


def cleanup_expired_sessions() -> int:
    """清除所有過期 session，回傳刪除筆數（供 server 啟動時呼叫）"""
    cutoff = datetime.fromtimestamp(
        _now_ts() - SESSION_TIMEOUT, tz=timezone.utc
    ).strftime('%Y-%m-%dT%H:%M:%SZ')
    conn = get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM sessions WHERE last_active < ?", (cutoff,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
