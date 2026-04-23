import json
from core.database import get_conn
from ._helpers import now_utc, hash_pin, verify_pin, audit


def get_config(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_config(key: str, value: str, operator: str | None = None):
    now = now_utc()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO config (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, now))
    if operator:
        audit(operator, None, "config_updated", "config", key, {"value": value})


def verify_admin_pin(pin: str) -> bool:
    raw = get_config("admin_pin")
    if not raw:
        return False
    data = json.loads(raw)
    return verify_pin(pin, data["hash"], data["salt"])


def set_admin_pin(new_pin: str, operator: str):
    h, s = hash_pin(new_pin)
    set_config("admin_pin", json.dumps({"hash": h, "salt": s}), operator)


def ensure_default_admin_pin():
    if not get_config("admin_pin"):
        set_admin_pin("1234", "system")
