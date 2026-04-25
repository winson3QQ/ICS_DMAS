from fastapi import APIRouter, HTTPException, Request

from auth.service import check_and_touch
from core.database import get_conn, get_schema_version
from repositories._helpers import audit
from auth.rbac import ROLE_HIERARCHY
from repositories.account_repo import (
    VALID_ROLES,
    clear_default_pin_flag,
    create_account,
    delete_account,
    get_account,
    get_all_accounts,
    suspend_all_accounts,
    update_account_pin,
    update_account_role,
    update_account_status,
)
from repositories.audit_repo import get_audit_log
from repositories.config_repo import (
    ADMIN_LOCKOUT_THRESHOLD,
    get_admin_pin_lock_status,
    get_config,
    record_admin_pin_failure,
    reset_admin_pin_failures,
    set_admin_pin,
    verify_admin_pin,
)
from repositories.pi_node_repo import (
    create_pi_node,
    delete_pi_node,
    list_pi_nodes,
    revoke_pi_node_key,
)
from schemas.admin import (
    AccountCreateIn,
    AccountStatusIn,
    AdminPinIn,
    PiNodeCreateIn,
    PinResetIn,
    RoleUpdateIn,
)

router = APIRouter(prefix="/api/admin", tags=["帳號管理"])


def _require_admin(request: Request) -> dict | None:
    """系統管理員專用（系統重置 / Admin PIN / Pi 節點）：
    1. 有效 session + role=系統管理員  ← 日常路徑
    2. 有效 Admin PIN header           ← break-glass
    """
    token = request.headers.get("X-Session-Token")
    if token:
        sess = check_and_touch(token)
        if sess and sess.get("role") == "系統管理員":
            return sess
    _check_admin_pin(request)
    return None


def _require_commander_or_pin(request: Request) -> dict | None:
    """帳號管理端點（指揮官可存取）：
    1. 有效 session + role=系統管理員 或 指揮官  ← 日常路徑
    2. 有效 Admin PIN header                      ← break-glass
    """
    token = request.headers.get("X-Session-Token")
    if token:
        sess = check_and_touch(token)
        if sess and sess.get("role") in ("系統管理員", "指揮官"):
            return sess
    _check_admin_pin(request)
    return None


def _check_admin_pin(request: Request):
    # Admin PIN 尚未完成初始設定
    if not get_config("admin_pin"):
        raise HTTPException(503, "Admin PIN 尚未設定，請查看伺服器啟動 log（~/.ics/admin_pin_token）")

    # C2-D：鎖定檢查（優先於 PIN 驗證）
    lock = get_admin_pin_lock_status()
    if lock["locked"]:
        raise HTTPException(423, f"管理員 PIN 已鎖定，請於 {lock['locked_until']} 後再試")

    pin = request.headers.get("X-Admin-PIN")
    if not pin:
        raise HTTPException(403, "管理員 PIN 驗證失敗")

    if not verify_admin_pin(pin):
        status = record_admin_pin_failure()
        if status["locked"]:
            raise HTTPException(
                423,
                f"管理員 PIN 連續錯誤 {status['failed_count']} 次，已鎖定 30 分鐘"
            )
        remaining = ADMIN_LOCKOUT_THRESHOLD - status["failed_count"]
        raise HTTPException(403, f"管理員 PIN 驗證失敗（剩餘 {remaining} 次）")

    # 驗證成功：清除失敗計數
    reset_admin_pin_failures()


def _check_no_escalation(sess: dict | None, target_username: str) -> None:
    """防止低權限角色管理高權限帳號。sess=None 表示 Admin PIN break-glass，直接放行。
    自我修改（同帳號）永遠允許。
    """
    if sess is None:
        return
    if sess.get("username") == target_username:
        return  # 允許自我修改（例如改自己的 PIN）
    actor_level  = ROLE_HIERARCHY.get(sess.get("role", ""), 0)
    target       = get_account(target_username)
    if target is None:
        raise HTTPException(404, "帳號不存在")
    target_level = ROLE_HIERARCHY.get(target["role"], 0)
    if actor_level <= target_level:
        raise HTTPException(403, "無法管理相同或更高權限的帳號")


# ── 狀態 ─────────────────────────────────────────────────────────────────────

@router.get("/status", tags=["帳號管理"])
def admin_status():
    raw = get_config("admin_pin")
    with get_conn() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
        schema_ver = get_schema_version(conn)
    return {"admin_pin_setup": raw is not None, "active_accounts": cnt,
            "schema_version": schema_ver}


@router.get("/schema-migrations", tags=["帳號管理"])
def list_migrations(request: Request):
    """C1-E：列出已套用的 schema migrations（需 Admin PIN）。"""
    _require_admin(request)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
        ).fetchall()
    return [dict(r) for r in rows]


# ── 帳號 CRUD ─────────────────────────────────────────────────────────────────

@router.get("/accounts")
def list_accounts(request: Request):
    _require_commander_or_pin(request)
    return get_all_accounts()


@router.post("/accounts")
def create_acct(body: AccountCreateIn, request: Request):
    caller = _require_commander_or_pin(request)
    if body.role not in VALID_ROLES:
        raise HTTPException(422, f"role 必須是 {' / '.join(sorted(VALID_ROLES))}")
    if len(body.pin) < 4 or len(body.pin) > 6 or not body.pin.isdigit():
        raise HTTPException(422, "PIN 必須是 4-6 位數字")
    # 指揮官 不能建立 系統管理員 帳號（防止 role 升級）
    if caller and caller.get("role") == "指揮官" and body.role == "系統管理員":
        raise HTTPException(403, "指揮官 無法建立 系統管理員 帳號")
    try:
        return create_account(body.username, body.pin, body.role,
                              body.display_name, body.role_detail)
    except Exception as e:
        raise HTTPException(409, f"帳號建立失敗：{e}") from e


@router.delete("/accounts/{username}")
def delete_acct(username: str, request: Request):
    sess = _require_commander_or_pin(request)
    _check_no_escalation(sess, username)
    if not delete_account(username, "admin"):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


@router.put("/accounts/{username}/status")
def update_status(username: str, body: AccountStatusIn, request: Request):
    sess = _require_commander_or_pin(request)
    _check_no_escalation(sess, username)
    if body.status not in ("active", "suspended"):
        raise HTTPException(422, "status 必須是 active 或 suspended")
    if not update_account_status(username, body.status, "admin"):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


@router.put("/accounts/{username}/pin")
def reset_pin(username: str, body: PinResetIn, request: Request):
    sess = _require_commander_or_pin(request)
    _check_no_escalation(sess, username)
    if len(body.new_pin) < 4 or len(body.new_pin) > 6 or not body.new_pin.isdigit():
        raise HTTPException(422, "PIN 必須是 4-6 位數字")
    if not update_account_pin(username, body.new_pin, "admin"):
        raise HTTPException(404, "帳號不存在")
    # C1-A：改 PIN 後清 is_default_pin 標記（首次設定流程結束）
    clear_default_pin_flag(username)
    return {"ok": True}


@router.put("/accounts/{username}/role")
def update_role(username: str, body: RoleUpdateIn, request: Request):
    sess = _require_commander_or_pin(request)
    _check_no_escalation(sess, username)
    if body.role not in VALID_ROLES:
        raise HTTPException(422, f"role 必須是 {' / '.join(sorted(VALID_ROLES))}")
    # 指揮官 不能將任何帳號 role 升級為 系統管理員
    if sess and sess.get("role") == "指揮官" and body.role == "系統管理員":
        raise HTTPException(403, "指揮官 無法指派 系統管理員 角色")
    if not update_account_role(username, body.role, "admin", body.role_detail):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


# ── Admin PIN ────────────────────────────────────────────────────────────────

@router.put("/pin")
def change_pin(body: AdminPinIn, request: Request):
    _require_admin(request)
    if len(body.new_pin) < 4 or len(body.new_pin) > 6 or not body.new_pin.isdigit():
        raise HTTPException(422, "PIN 必須是 4-6 位數字")
    set_admin_pin(body.new_pin, "admin")
    return {"ok": True}


# ── 系統操作 ─────────────────────────────────────────────────────────────────

@router.post("/reset-db", tags=["系統"])
def reset_db(request: Request):
    _require_admin(request)
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
    _require_admin(request)
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
    _require_admin(request)
    count = suspend_all_accounts("admin")
    return {"ok": True, "suspended_count": count}


@router.get("/audit-log")
def audit_log(request: Request, limit: int = 100):
    _require_commander_or_pin(request)
    return get_audit_log(limit)


# ── Pi 節點管理 ───────────────────────────────────────────────────────────────

@router.get("/pi-nodes", tags=["Pi 節點"])
def list_nodes(request: Request):
    _require_admin(request)
    return list_pi_nodes()


@router.post("/pi-nodes", tags=["Pi 節點"])
def create_node(body: PiNodeCreateIn, request: Request):
    _require_admin(request)
    allowed = ("shelter", "medical", "forward", "security")
    if body.unit_id not in allowed:
        raise HTTPException(422, f"unit_id 必須是 {allowed} 之一")
    try:
        return create_pi_node(body.unit_id, body.label)
    except Exception as e:
        if "UNIQUE" in str(e) or "PRIMARY" in str(e):
            raise HTTPException(409, f"unit_id '{body.unit_id}' 已存在") from e
        raise


@router.delete("/pi-nodes/{unit_id}", tags=["Pi 節點"])
def delete_node(unit_id: str, request: Request):
    _require_admin(request)
    if not delete_pi_node(unit_id):
        raise HTTPException(404, "Pi 節點不存在")
    return {"ok": True}


@router.post("/pi-nodes/{unit_id}/rekey", tags=["Pi 節點"])
def rekey_node(unit_id: str, request: Request):
    _require_admin(request)
    result = revoke_pi_node_key(unit_id)
    if not result:
        raise HTTPException(404, "Pi 節點不存在")
    return result
