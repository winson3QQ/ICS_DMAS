from fastapi import APIRouter, HTTPException, Request
from core.database import get_conn
from repositories.account_repo import (
    create_account, get_all_accounts, update_account_status,
    update_account_pin, update_account_role, delete_account, suspend_all_accounts,
)
from repositories.config_repo import get_config, verify_admin_pin, set_admin_pin
from repositories.pi_node_repo import (
    create_pi_node, list_pi_nodes, delete_pi_node, revoke_pi_node_key,
)
from repositories.audit_repo import get_audit_log
from repositories._helpers import audit
from schemas.admin import (
    AccountCreateIn, AccountStatusIn, PinResetIn,
    AdminPinIn, RoleUpdateIn, PiNodeCreateIn,
)

router = APIRouter(prefix="/api/admin", tags=["帳號管理"])


def _check_admin_pin(request: Request):
    pin = request.headers.get("X-Admin-PIN")
    if not pin or not verify_admin_pin(pin):
        raise HTTPException(403, "管理員 PIN 驗證失敗")


# ── 狀態 ─────────────────────────────────────────────────────────────────────

@router.get("/status", tags=["帳號管理"])
def admin_status():
    raw = get_config("admin_pin")
    with get_conn() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
    return {"admin_pin_setup": raw is not None, "active_accounts": cnt}


# ── 帳號 CRUD ─────────────────────────────────────────────────────────────────

@router.get("/accounts")
def list_accounts(request: Request):
    _check_admin_pin(request)
    return get_all_accounts()


@router.post("/accounts")
def create_acct(body: AccountCreateIn, request: Request):
    _check_admin_pin(request)
    if body.role not in ("指揮官", "操作員"):
        raise HTTPException(422, "role 必須是 指揮官 或 操作員")
    if len(body.pin) < 4 or len(body.pin) > 6 or not body.pin.isdigit():
        raise HTTPException(422, "PIN 必須是 4-6 位數字")
    try:
        return create_account(body.username, body.pin, body.role,
                              body.display_name, body.role_detail)
    except Exception as e:
        raise HTTPException(409, f"帳號建立失敗：{e}")


@router.delete("/accounts/{username}")
def delete_acct(username: str, request: Request):
    _check_admin_pin(request)
    if not delete_account(username, "admin"):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


@router.put("/accounts/{username}/status")
def update_status(username: str, body: AccountStatusIn, request: Request):
    _check_admin_pin(request)
    if body.status not in ("active", "suspended"):
        raise HTTPException(422, "status 必須是 active 或 suspended")
    if not update_account_status(username, body.status, "admin"):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


@router.put("/accounts/{username}/pin")
def reset_pin(username: str, body: PinResetIn, request: Request):
    _check_admin_pin(request)
    if len(body.new_pin) < 4 or len(body.new_pin) > 6 or not body.new_pin.isdigit():
        raise HTTPException(422, "PIN 必須是 4-6 位數字")
    if not update_account_pin(username, body.new_pin, "admin"):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


@router.put("/accounts/{username}/role")
def update_role(username: str, body: RoleUpdateIn, request: Request):
    _check_admin_pin(request)
    if body.role not in ("指揮官", "操作員"):
        raise HTTPException(422, "role 必須是 指揮官 或 操作員")
    if not update_account_role(username, body.role, "admin", body.role_detail):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


# ── Admin PIN ────────────────────────────────────────────────────────────────

@router.put("/pin")
def change_pin(body: AdminPinIn, request: Request):
    _check_admin_pin(request)
    if len(body.new_pin) < 4 or len(body.new_pin) > 6 or not body.new_pin.isdigit():
        raise HTTPException(422, "PIN 必須是 4-6 位數字")
    set_admin_pin(body.new_pin, "admin")
    return {"ok": True}


# ── 系統操作 ─────────────────────────────────────────────────────────────────

@router.post("/reset-db", tags=["系統"])
def reset_db(request: Request):
    _check_admin_pin(request)
    tables = ["snapshots", "events", "decisions", "predictions",
              "manual_records", "sync_log", "pi_received_batches", "audit_log",
              "ttx_injects", "exercises", "resource_snapshots", "aar_entries",
              "ai_recommendations"]
    with get_conn() as conn:
        for t in tables:
            try:
                conn.execute(f"DELETE FROM {t}")  # nosec B608
            except Exception:
                pass
    audit("admin", None, "db_reset", "system", "all", {"tables": tables})
    return {"ok": True, "cleared_tables": tables}


@router.post("/reset-exercise", tags=["系統"])
def reset_exercise(request: Request):
    _check_admin_pin(request)
    ex_tables = ["ttx_injects", "exercises", "resource_snapshots", "aar_entries", "ai_recommendations"]
    data_tables = ["snapshots", "events", "decisions", "manual_records", "audit_log"]
    cleared = {}
    with get_conn() as conn:
        for t in ex_tables:
            try:
                cur = conn.execute(f"DELETE FROM {t}")  # nosec B608
                cleared[t] = cur.rowcount
            except Exception:
                pass
        for t in data_tables:
            try:
                cur = conn.execute(f"DELETE FROM {t} WHERE exercise_id IS NOT NULL")  # nosec B608
                cleared[t] = cur.rowcount
            except Exception:
                pass
    audit("admin", None, "exercise_reset", "system", "all", {"cleared": cleared})
    return {"ok": True, "cleared": cleared}


@router.post("/suspend-all")
def suspend_all(request: Request):
    _check_admin_pin(request)
    count = suspend_all_accounts("admin")
    return {"ok": True, "suspended_count": count}


@router.get("/audit-log")
def audit_log(request: Request, limit: int = 100):
    _check_admin_pin(request)
    return get_audit_log(limit)


# ── Pi 節點管理 ───────────────────────────────────────────────────────────────

@router.get("/pi-nodes", tags=["Pi 節點"])
def list_nodes(request: Request):
    _check_admin_pin(request)
    return list_pi_nodes()


@router.post("/pi-nodes", tags=["Pi 節點"])
def create_node(body: PiNodeCreateIn, request: Request):
    _check_admin_pin(request)
    allowed = ("shelter", "medical", "forward", "security")
    if body.unit_id not in allowed:
        raise HTTPException(422, f"unit_id 必須是 {allowed} 之一")
    try:
        return create_pi_node(body.unit_id, body.label)
    except Exception as e:
        if "UNIQUE" in str(e) or "PRIMARY" in str(e):
            raise HTTPException(409, f"unit_id '{body.unit_id}' 已存在")
        raise


@router.delete("/pi-nodes/{unit_id}", tags=["Pi 節點"])
def delete_node(unit_id: str, request: Request):
    _check_admin_pin(request)
    if not delete_pi_node(unit_id):
        raise HTTPException(404, "Pi 節點不存在")
    return {"ok": True}


@router.post("/pi-nodes/{unit_id}/rekey", tags=["Pi 節點"])
def rekey_node(unit_id: str, request: Request):
    _check_admin_pin(request)
    result = revoke_pi_node_key(unit_id)
    if not result:
        raise HTTPException(404, "Pi 節點不存在")
    return result
