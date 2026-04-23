"""
repositories/_helpers.py — 共用 DB 工具函式
"""

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta

from core.database import get_conn


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_utc(s: str | None) -> str | None:
    """各種時間格式正規化為 ISO 8601 UTC+Z，None 回 None"""
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        return s
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    if "+" in s or (s.count("-") > 2):
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
    return s + "Z"


def add_minutes(iso_str: str, minutes: int) -> str:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return (dt + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if "extra" in d and d["extra"]:
        try:
            d["extra"] = json.loads(d["extra"])
        except Exception:
            pass
    return d


def audit(operator: str, device_id: str | None,
          action_type: str, target_table: str, target_id: str,
          detail: dict, exercise_id: int | None = None):
    sql = """
        INSERT INTO audit_log
            (operator, device_id, action_type, target_table, target_id,
             detail, exercise_id, created_at)
        VALUES (?,?,?,?,?,?,?,?)
    """
    with get_conn() as conn:
        conn.execute(sql, (
            operator, device_id, action_type,
            target_table, str(target_id),
            json.dumps(detail, ensure_ascii=False),
            exercise_id,
            now_utc(),
        ))


# ── PIN hashing（PBKDF2-SHA256, 100k iterations）──────────────────────────

def hash_pin(pin: str, salt_hex: str | None = None) -> tuple[str, str]:
    if salt_hex is None:
        salt = os.urandom(16)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)
    h = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100_000)
    return h.hex(), salt_hex


def verify_pin(pin: str, stored_hash: str, stored_salt: str) -> bool:
    h, _ = hash_pin(pin, stored_salt)
    return h == stored_hash
