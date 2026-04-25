"""
auth/rbac.py — Role-Based Access Control Dependency（C1-A Phase 2）

ROLE_HIERARCHY：數值越高代表權限越高，向上相容。
  系統管理員(4) > 指揮官(3) > 操作員(2) > 觀察員(1)

用法：
    from auth.rbac import require_role

    @router.post("/events")
    def create_event(body: EventIn, _: dict = require_role("操作員")):
        ...

    require_role("操作員") 允許 操作員、指揮官、系統管理員 通過；觀察員被擋。
    ICS 原則：指揮官在緊急狀況必須能直接操作，不能被 role gate 擋下（向上相容）。
"""

from fastapi import Depends, HTTPException, Request

from auth.service import validate_session

ROLE_HIERARCHY: dict[str, int] = {
    "系統管理員": 4,
    "指揮官":     3,
    "操作員":     2,
    "觀察員":     1,
}


def check_role_level(session: dict, *allowed: str) -> bool:
    """純函數：session role 是否達到 allowed 中任一 role 的最低等級。

    測試友善：不依賴 Request / DB，可直接 unit test。
    """
    min_level = min(ROLE_HIERARCHY[r] for r in allowed)
    user_level = ROLE_HIERARCHY.get(session.get("role", ""), 0)
    return user_level >= min_level


def require_role(*allowed: str) -> object:
    """FastAPI Dependency factory。

    回傳 Depends() 物件，直接作為 handler 參數預設值：
        def handler(_: dict = require_role("操作員")):

    通過時回傳 session dict；失敗時拋：
      - 401 — 無有效 session（由 validate_session 拋出）
      - 403 — session 有效但 role 不足
    """
    if not allowed:
        raise ValueError("require_role 至少需要一個 role")
    unknown = set(allowed) - set(ROLE_HIERARCHY)
    if unknown:
        raise ValueError(f"未知 role：{unknown}")

    def _dependency(request: Request) -> dict:
        sess = validate_session(request)
        if not check_role_level(sess, *allowed):
            label = " 或 ".join(
                sorted(allowed, key=lambda r: -ROLE_HIERARCHY[r])
            )
            raise HTTPException(403, f"權限不足（需要 {label}）")
        return sess

    return Depends(_dependency)
