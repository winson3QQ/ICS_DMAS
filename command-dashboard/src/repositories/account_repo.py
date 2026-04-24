import uuid
from datetime import datetime, timedelta, timezone
from core.database import get_conn
from ._helpers import now_utc, hash_pin, verify_pin, audit


# ── C1-A 登入鎖定參數 ───────────────────────────────────────────
LOCKOUT_THRESHOLD = 5            # 連續失敗次數
LOCKOUT_DURATION_MIN = 15        # 鎖定時長（分鐘）


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _iso_to_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _is_locked(row: dict) -> bool:
    """檢查 row 是否仍在鎖定中。"""
    locked_until = row.get("locked_until")
    if not locked_until:
        return False
    return datetime.now(timezone.utc) < _iso_to_dt(locked_until)


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


def verify_login(username: str, pin: str) -> tuple[dict | None, str]:
    """驗證登入。

    回傳 (account_dict_or_None, reason)
      - ("ok", account)：成功
      - (None, "no_user")：帳號不存在
      - (None, "suspended")：帳號被停權
      - (None, "locked")：帳號鎖定中（5 次失敗 / 15 分鐘）
      - (None, "bad_pin")：PIN 錯誤（已 +1 失敗計數）
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE username=?", (username,)).fetchone()
        if not row:
            return None, "no_user"
        d = dict(row)
        if d["status"] != "active":
            return None, "suspended"
        # 鎖定中？
        if _is_locked(d):
            return None, "locked"
        # 驗證 PIN
        if not verify_pin(pin, d["pin_hash"], d["pin_salt"]):
            # +1 失敗計數，若達門檻則鎖定
            new_count = (d.get("failed_login_count") or 0) + 1
            locked_until = None
            if new_count >= LOCKOUT_THRESHOLD:
                locked_until = (
                    datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MIN)
                ).strftime('%Y-%m-%dT%H:%M:%SZ')
            conn.execute(
                "UPDATE accounts SET failed_login_count=?, locked_until=? WHERE username=?",
                (new_count, locked_until, username))
            conn.commit()
            if locked_until:
                audit(username, None, "account_locked", "accounts", username,
                      {"failed_count": new_count, "locked_until": locked_until})
                return None, "locked"
            return None, "bad_pin"
        # 成功：清失敗計數 + 更新 last_login
        conn.execute(
            "UPDATE accounts SET failed_login_count=0, locked_until=NULL, last_login=? WHERE username=?",
            (_iso_now(), username))
        conn.commit()
    d.pop("pin_hash", None)
    d.pop("pin_salt", None)
    return d, "ok"


def unlock_account(username: str, operator: str) -> bool:
    """管理員手動解鎖（清失敗計數 + 鎖定時間）。"""
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET failed_login_count=0, locked_until=NULL WHERE username=?",
            (username,))
    if cur.rowcount:
        audit(operator, None, "account_unlocked", "accounts", username, {})
    return cur.rowcount > 0


def ensure_default_admin(default_pin: str = "1234") -> None:
    """首次啟動：若無帳號則建立預設 admin（舊版 fallback，僅測試/相容用）。

    ⚠️ C1-A 後新部署應呼叫 ensure_initial_admin_token()，會：
       - 產生隨機 6 位數 PIN（不再寫死 1234）
       - 印至 console + 寫 ~/.ics/first_run_token
       - 標記 is_default_pin=1，登入後強制改密碼
    """
    with get_conn() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
    if cnt == 0:
        create_account("admin", default_pin, "指揮官", "系統管理員", "admin")
        # 標記為預設 PIN，登入後強制改
        with get_conn() as conn:
            conn.execute(
                "UPDATE accounts SET is_default_pin=1 WHERE username='admin'")
            conn.commit()


def ensure_initial_admin_token(token_dir: str | None = None) -> str | None:
    """首次啟動：若無帳號，產生隨機 6 位數 PIN 建立 admin。

    回傳產生的 PIN（首次）或 None（已有帳號）。
    PIN 同時寫入 ~/.ics/first_run_token（chmod 600），方便 operator 看到後抹除。
    """
    import os
    import secrets
    import logging

    with get_conn() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
    if cnt > 0:
        return None

    # 6 位數 PIN（不可預測）；100 萬種組合配合 5 次/15 分鐘鎖定足夠抵擋暴力
    initial_pin = f"{secrets.randbelow(1_000_000):06d}"
    create_account("admin", initial_pin, "指揮官", "系統管理員", "admin")
    with get_conn() as conn:
        conn.execute(
            "UPDATE accounts SET is_default_pin=1 WHERE username='admin'")
        conn.commit()

    # 寫 token 檔（C3-B install.sh 會建好權限）
    target_dir = token_dir or os.path.expanduser("~/.ics")
    try:
        os.makedirs(target_dir, mode=0o700, exist_ok=True)
        token_file = os.path.join(target_dir, "first_run_token")
        with open(token_file, "w") as f:
            f.write(initial_pin + "\n")
        os.chmod(token_file, 0o600)
    except OSError:
        pass  # 寫檔失敗不阻擋啟動（log 已印 PIN）

    # console 印（醒目，operator 第一次啟動會看到）
    logger = logging.getLogger("ics.first_run")
    logger.warning("=" * 60)
    logger.warning("ICS 首次啟動：admin 初始 PIN = %s", initial_pin)
    logger.warning("登入後請立刻修改 PIN（系統會強制要求）")
    logger.warning("Token 檔：%s（首次登入後請手動刪除）", token_file)
    logger.warning("=" * 60)
    return initial_pin


def clear_default_pin_flag(username: str) -> bool:
    """改 PIN 成功後呼叫，清 is_default_pin 標記。"""
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET is_default_pin=0 WHERE username=?", (username,))
        conn.commit()
    return cur.rowcount > 0


def is_first_run_required() -> bool:
    """是否仍有 is_default_pin=1 的 admin 帳號（用於 422 gate 檢查）。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM accounts WHERE is_default_pin=1 AND role='指揮官'"
        ).fetchone()
    return row["c"] > 0
