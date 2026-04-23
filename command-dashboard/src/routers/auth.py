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
    acct = verify_login(body.username, body.pin)
    if not acct:
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
