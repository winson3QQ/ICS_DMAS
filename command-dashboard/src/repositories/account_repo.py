import uuid
from core.database import get_conn
from ._helpers import now_utc, hash_pin, verify_pin, audit


def create_account(username: str, pin: str, role: str = "操作員",
                   display_name: str | None = None,
                   role_detail: str | None = None) -> dict:
    pin_hash, pin_salt = hash_pin(pin)
    now = now_utc()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO accounts
               (username, pin_hash, pin_salt, role, role_detail, display_name, status, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (username, pin_hash, pin_salt, role, role_detail, display_name, "active", now))
    audit("admin", None, "account_created", "accounts", username, {"role": role})
    return {"username": username, "role": role, "role_detail": role_detail,
            "status": "active", "created_at": now}


def get_all_accounts() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT username, role, role_detail, display_name, status, created_at, updated_at "
            "FROM accounts ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def update_account_status(username: str, status: str, operator: str) -> bool:
    now = now_utc()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET status=?, updated_at=? WHERE username=?",
            (status, now, username))
    if cur.rowcount:
        audit(operator, None, "account_status_updated", "accounts", username, {"status": status})
    return cur.rowcount > 0


def update_account_pin(username: str, new_pin: str, operator: str) -> bool:
    pin_hash, pin_salt = hash_pin(new_pin)
    now = now_utc()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET pin_hash=?, pin_salt=?, updated_at=? WHERE username=?",
            (pin_hash, pin_salt, now, username))
    if cur.rowcount:
        audit(operator, None, "account_pin_reset", "accounts", username, {})
    return cur.rowcount > 0


def update_account_role(username: str, role: str, operator: str,
                        role_detail: str | None = None) -> bool:
    now = now_utc()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET role=?, role_detail=?, updated_at=? WHERE username=?",
            (role, role_detail, now, username))
    if cur.rowcount:
        audit(operator, None, "account_role_updated", "accounts", username,
              {"role": role, "role_detail": role_detail})
    return cur.rowcount > 0


def delete_account(username: str, operator: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM accounts WHERE username=?", (username,))
    if cur.rowcount:
        audit(operator, None, "account_deleted", "accounts", username, {})
    return cur.rowcount > 0


def suspend_all_accounts(operator: str) -> int:
    now = now_utc()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET status='suspended', updated_at=? WHERE status='active'", (now,))
    audit(operator, None, "all_accounts_suspended", "accounts", "*", {})
    return cur.rowcount


def verify_login(username: str, pin: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE username=?", (username,)).fetchone()
    if not row:
        return None
    d = dict(row)
    if d["status"] != "active":
        return None
    if not verify_pin(pin, d["pin_hash"], d["pin_salt"]):
        return None
    d.pop("pin_hash", None)
    d.pop("pin_salt", None)
    return d


def ensure_default_admin(default_pin: str = "1234") -> None:
    """首次啟動：若無帳號則建立預設 admin"""
    with get_conn() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
    if cnt == 0:
        create_account("admin", default_pin, "指揮官", "系統管理員", "admin")
