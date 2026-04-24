from fastapi import APIRouter, HTTPException, Request
from repositories.account_repo import verify_login
from repositories.audit_repo import get_audit_log
from repositories._helpers import audit
from auth.service import (
    create_session, validate_session, destroy_session, session_remaining
)
from schemas.auth import LoginIn

router = APIRouter(prefix="/api/auth", tags=["認證"])


@router.post("/login")
def login(body: LoginIn):
    acct, reason = verify_login(body.username, body.pin)
    if reason == "locked":
        # 423 Locked：明確告知鎖定，不洩漏帳號是否存在
        raise HTTPException(423, "帳號暫時鎖定，請 15 分鐘後再試")
    if reason == "suspended":
        raise HTTPException(403, "帳號已停權")
    if not acct:
        # no_user 與 bad_pin 同樣訊息（不洩漏帳號是否存在）
        raise HTTPException(401, "帳號或 PIN 錯誤")
    token = create_session(acct)
    audit(acct["username"], None, "login", "accounts", acct["username"],
          {"role": acct["role"]})
    return {
        "ok":           True,
        "session_id":   token,
        "username":     acct["username"],
        "role":         acct["role"],
        "role_detail":  acct.get("role_detail"),
        "display_name": acct.get("display_name") or acct["username"],
        # C1-A：is_default_pin=1 → 前端強制改 PIN
        "must_change_pin": bool(acct.get("is_default_pin")),
    }


@router.post("/logout")
def logout(request: Request):
    token = request.headers.get("X-Session-Token")
    sess  = destroy_session(token) if token else None
    if sess:
        audit(sess["username"], None, "logout", "accounts", sess["username"], {})
    return {"ok": True}


@router.get("/heartbeat")
def heartbeat(request: Request):
    sess      = validate_session(request)
    remaining = session_remaining(request.headers.get("X-Session-Token", ""))
    return {"ok": True, "remaining": remaining,
            "username": sess["username"], "role": sess["role"],
            "role_detail": sess.get("role_detail")}


@router.get("/me")
def me(request: Request):
    sess = validate_session(request)
    return {
        "username":     sess["username"],
        "role":         sess["role"],
        "role_detail":  sess.get("role_detail"),
        "display_name": sess.get("display_name", sess["username"]),
    }
