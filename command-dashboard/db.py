"""
db.py — ICS 指揮部後端
SQLite schema 定義 + CRUD 函式

設計原則：
- AUDIT_LOG 只能 INSERT，禁止 UPDATE / DELETE
- SNAPSHOT 以 snapshot_id（外部 UUID）做 upsert，避免重複
- DECISION 狀態機：pending → approved/hold/redirect；closure 用新增記錄
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "ics.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # 多讀一寫，適合 Pi
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ──────────────────────────────────────────
# Schema 建立
# ──────────────────────────────────────────

SCHEMA = """
-- 各節點快照（趨勢計算用）
CREATE TABLE IF NOT EXISTS snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id     TEXT    UNIQUE NOT NULL,   -- 外部 UUID（各組 PWA 產生）
    snapshot_time   TEXT    NOT NULL,          -- ISO 8601 UTC
    node_type       TEXT    NOT NULL,          -- medical/shelter/forward/ccp/evac/security
    source          TEXT    NOT NULL DEFAULT 'auto',  -- auto/qr_scan/auto_sync/manual
    -- 通用欄位
    casualties_red    INTEGER,
    casualties_yellow INTEGER,
    casualties_green  INTEGER,
    casualties_black  INTEGER,
    bed_used          INTEGER,
    bed_total         INTEGER,
    waiting_count     INTEGER,
    pending_evac      INTEGER,
    vehicle_available INTEGER,
    staff_on_duty     INTEGER,
    extra             TEXT,   -- JSON，各組特有欄位（物資量等）
    received_at     TEXT    NOT NULL           -- 指揮部收到的時間
);

-- 事件記錄
CREATE TABLE IF NOT EXISTS events (
    id                      TEXT PRIMARY KEY,  -- UUID
    reported_by_unit        TEXT NOT NULL,
    location_desc           TEXT,
    event_type              TEXT NOT NULL,
    severity                TEXT NOT NULL DEFAULT 'info',  -- critical/warning/info
    status                  TEXT NOT NULL DEFAULT 'open',  -- open/in_progress/resolved/closed
    response_type           TEXT,
    needs_commander_decision INTEGER NOT NULL DEFAULT 0,   -- 0/1
    description             TEXT NOT NULL,
    related_person_name     TEXT,
    occurred_at             TEXT NOT NULL,
    resolved_at             TEXT,
    operator_name           TEXT NOT NULL,
    created_at              TEXT NOT NULL
);

-- 待裁示事項（決策主題）
CREATE TABLE IF NOT EXISTS decisions (
    id                  TEXT PRIMARY KEY,  -- UUID
    primary_event_id    TEXT REFERENCES events(id),
    decision_seq        INTEGER NOT NULL DEFAULT 1,
    parent_decision_id  TEXT REFERENCES decisions(id),
    decision_type       TEXT NOT NULL,  -- initial/revision/escalation/closure
    severity            TEXT NOT NULL,  -- critical/warning
    decision_title      TEXT NOT NULL,
    impact_description  TEXT NOT NULL,
    suggested_action_a  TEXT NOT NULL,
    suggested_action_b  TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
        -- pending/approved/hold/redirect/completed/superseded
    decided_by          TEXT,
    decided_at          TEXT,
    execution_note      TEXT,
    superseded_by       TEXT REFERENCES decisions(id),
    closed_at           TEXT,
    created_by          TEXT NOT NULL,
    created_at          TEXT NOT NULL
);

-- 稽核日誌（不可刪除、不可修改）
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    operator    TEXT,
    device_id   TEXT,
    action_type TEXT NOT NULL,
        -- snapshot_received/event_created/decision_created/decision_made
        -- data_export/login/manual_input
    target_table TEXT,
    target_id    TEXT,
    detail       TEXT,   -- JSON
    created_at   TEXT NOT NULL
);

-- 手動輸入記錄（通用暫存表，涵蓋無對應 API 的表單）
-- 包含：人員入站/SRT/CMIST/離站、傷患記錄、車輛狀態、局勢摘要
CREATE TABLE IF NOT EXISTS manual_records (
    id          TEXT PRIMARY KEY,   -- UUID
    form_id     TEXT NOT NULL,      -- shelter-intake / med-patient / ...
    form_type   TEXT NOT NULL,      -- 對應規格的類型標籤
    target_table TEXT NOT NULL,     -- 預計寫入的資料表名稱
    operator    TEXT NOT NULL,
    summary     TEXT,               -- 一行摘要，供審核介面顯示
    payload     TEXT NOT NULL,      -- JSON，完整表單資料
    sync_status TEXT NOT NULL DEFAULT 'pending',
        -- pending（待同步）/ synced（已同步）/ skipped（人工略過）
    submitted_at TEXT NOT NULL,
    synced_at    TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_snapshots_node_time
    ON snapshots(node_type, snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_events_status
    ON events(status, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_status
    ON decisions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_parent
    ON decisions(parent_decision_id);
CREATE INDEX IF NOT EXISTS idx_manual_records_status
    ON manual_records(sync_status, submitted_at DESC);
"""


def init_db():
    """建立所有資料表（idempotent）"""
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ──────────────────────────────────────────
# SNAPSHOT CRUD
# ──────────────────────────────────────────

def upsert_snapshot(data: dict) -> dict:
    """
    寫入一筆快照。若 snapshot_id 已存在則忽略（idempotent）。
    回傳 {inserted: bool, id: int}
    """
    now = _now()
    extra = data.get("extra") or {}

    # 從 QR-MEDICAL 的 supplies 結構搬到 extra
    if "supplies" in data:
        extra["supplies"] = data["supplies"]
    if "units" in data:
        extra["units"] = data["units"]   # QR-FORWARD 多小隊
    if "srt" in data:
        extra["srt"] = data["srt"]
    if "pending_intake" in data:
        extra["pending_intake"] = data["pending_intake"]
    if "cmist_pending" in data:
        extra["cmist_pending"] = data["cmist_pending"]
    if "post_total" in data:
        extra["post_total"] = data["post_total"]
    if "post_anomaly" in data:
        extra["post_anomaly"] = data["post_anomaly"]
    if "qrf_available" in data:
        extra["qrf_available"] = data["qrf_available"]
    if "isolation_count" in data:
        extra["isolation_count"] = data["isolation_count"]

    sql = """
        INSERT OR IGNORE INTO snapshots
            (snapshot_id, snapshot_time, node_type, source,
             casualties_red, casualties_yellow, casualties_green, casualties_black,
             bed_used, bed_total, waiting_count, pending_evac,
             vehicle_available, staff_on_duty, extra, received_at)
        VALUES
            (?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?, ?)
    """
    casualties = data.get("casualties", {})
    with get_conn() as conn:
        cur = conn.execute(sql, (
            data["snapshot_id"],
            data["t"],
            data["node_type"],
            data.get("source", "auto"),
            casualties.get("red")   or data.get("casualties_red"),
            casualties.get("yellow")or data.get("casualties_yellow"),
            casualties.get("green") or data.get("casualties_green"),
            casualties.get("black") or data.get("casualties_black"),
            data.get("bed_used"),
            data.get("bed_total"),
            data.get("waiting_count"),
            data.get("pending_evac"),
            data.get("vehicle_available"),
            data.get("staff_on_duty"),
            json.dumps(extra, ensure_ascii=False) if extra else None,
            now,
        ))
        inserted = cur.rowcount > 0
        row_id   = cur.lastrowid if inserted else None

    _audit("system", None, "snapshot_received",
           "snapshots", data["snapshot_id"],
           {"node_type": data["node_type"], "source": data.get("source","auto"), "inserted": inserted})

    return {"inserted": inserted, "snapshot_id": data["snapshot_id"]}


def get_snapshots(node_type: str, limit: int = 20) -> list[dict]:
    """取最近 N 筆快照（依 snapshot_time 倒序）"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE node_type=? ORDER BY snapshot_time DESC LIMIT ?",
            (node_type, limit)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_latest_snapshot(node_type: str) -> dict | None:
    rows = get_snapshots(node_type, limit=1)
    return rows[0] if rows else None


# ──────────────────────────────────────────
# EVENT CRUD
# ──────────────────────────────────────────

def create_event(data: dict) -> dict:
    eid = str(uuid.uuid4())
    now = _now()
    sql = """
        INSERT INTO events
            (id, reported_by_unit, location_desc, event_type, severity,
             status, response_type, needs_commander_decision, description,
             related_person_name, occurred_at, operator_name, created_at)
        VALUES (?,?,?,?,?, ?,?,?,?, ?,?,?,?)
    """
    with get_conn() as conn:
        conn.execute(sql, (
            eid,
            data["reported_by_unit"],
            data.get("location_desc"),
            data["event_type"],
            data.get("severity", "info"),
            "open",
            data.get("response_type"),
            1 if data.get("needs_commander_decision") else 0,
            data["description"],
            data.get("related_person_name"),
            data.get("occurred_at", now),
            data["operator_name"],
            now,
        ))
    _audit(data["operator_name"], None, "event_created",
           "events", eid, {"event_type": data["event_type"], "severity": data.get("severity","info")})
    return {"id": eid}


def get_events(status: str | None = None, limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM events WHERE status=? ORDER BY occurred_at DESC LIMIT ?",
                (status, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY occurred_at DESC LIMIT ?",
                (limit,)).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_event_status(event_id: str, status: str, operator: str):
    with get_conn() as conn:
        conn.execute("UPDATE events SET status=? WHERE id=?", (status, event_id))
    _audit(operator, None, "event_status_updated", "events", event_id, {"status": status})


# ──────────────────────────────────────────
# DECISION CRUD
# ──────────────────────────────────────────

def create_decision(data: dict) -> dict:
    did = str(uuid.uuid4())
    now = _now()

    # 計算 decision_seq
    seq = 1
    if data.get("parent_decision_id"):
        # 找根節點，數整條鏈的長度
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT COUNT(*) as cnt FROM decisions WHERE "
                "parent_decision_id IS NOT NULL AND "
                "(id=? OR parent_decision_id=?)",
                (data["parent_decision_id"], data["parent_decision_id"])
            ).fetchone()
        seq = (rows["cnt"] or 0) + 2

    sql = """
        INSERT INTO decisions
            (id, primary_event_id, decision_seq, parent_decision_id,
             decision_type, severity, decision_title, impact_description,
             suggested_action_a, suggested_action_b, status,
             created_by, created_at)
        VALUES (?,?,?,?, ?,?,?,?, ?,?,?, ?,?)
    """
    with get_conn() as conn:
        conn.execute(sql, (
            did,
            data.get("primary_event_id"),
            seq,
            data.get("parent_decision_id"),
            data["decision_type"],
            data["severity"],
            data["decision_title"],
            data["impact_description"],
            data["suggested_action_a"],
            data.get("suggested_action_b"),
            "pending",
            data["created_by"],
            now,
        ))
        # 若有 parent，將上一筆標記為 superseded
        if data.get("parent_decision_id"):
            conn.execute(
                "UPDATE decisions SET status='superseded', superseded_by=? WHERE id=?",
                (did, data["parent_decision_id"])
            )

    _audit(data["created_by"], None, "decision_created", "decisions", did,
           {"title": data["decision_title"], "severity": data["severity"],
            "type": data["decision_type"]})
    return {"id": did}


def decide(decision_id: str, action: str, decided_by: str, execution_note: str = "") -> dict:
    """
    action: approved / hold / redirect / completed
    Write-Freeze 後不可再修改（除非是 closure 新增一筆）
    """
    valid_actions = {"approved", "hold", "redirect", "completed"}
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}")

    now = _now()
    with get_conn() as conn:
        row = conn.execute("SELECT status FROM decisions WHERE id=?", (decision_id,)).fetchone()
        if not row:
            raise ValueError("Decision not found")
        if row["status"] not in ("pending",):
            raise ValueError(f"Decision already decided: {row['status']}")
        conn.execute(
            "UPDATE decisions SET status=?, decided_by=?, decided_at=?, execution_note=? WHERE id=?",
            (action, decided_by, now, execution_note, decision_id)
        )

    _audit(decided_by, None, "decision_made", "decisions", decision_id,
           {"action": action, "execution_note": execution_note})
    return {"id": decision_id, "status": action, "decided_at": now}


def get_decisions(status: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE status=? ORDER BY created_at DESC",
                (status,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM decisions ORDER BY created_at DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


# ──────────────────────────────────────────
# AUDIT LOG（只寫，不讀）
# ──────────────────────────────────────────

def _audit(operator: str, device_id: str | None,
           action_type: str, target_table: str, target_id: str, detail: dict):
    sql = """
        INSERT INTO audit_log
            (operator, device_id, action_type, target_table, target_id, detail, created_at)
        VALUES (?,?,?,?,?,?,?)
    """
    with get_conn() as conn:
        conn.execute(sql, (
            operator, device_id, action_type,
            target_table, str(target_id),
            json.dumps(detail, ensure_ascii=False),
            _now()
        ))


def get_audit_log(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


# ──────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # extra 欄位自動反序列化
    if "extra" in d and d["extra"]:
        try:
            d["extra"] = json.loads(d["extra"])
        except Exception:
            pass
    return d


# ──────────────────────────────────────────
# MANUAL RECORDS CRUD
# ──────────────────────────────────────────

def create_manual_record(data: dict) -> dict:
    """
    儲存一筆手動輸入記錄。
    適用於沒有直接對應 API 端點的表單：
    shelter-intake, shelter-srt, shelter-cmist, shelter-exit,
    med-patient, intel-vehicle, intel-situation
    """
    rid  = str(uuid.uuid4())
    now  = _now()
    payload = data.get("payload", {})

    sql = """
        INSERT INTO manual_records
            (id, form_id, form_type, target_table, operator,
             summary, payload, sync_status, submitted_at)
        VALUES (?,?,?,?,?, ?,?,?,?)
    """
    with get_conn() as conn:
        conn.execute(sql, (
            rid,
            data["form_id"],
            data["form_type"],
            data["target_table"],
            data["operator"],
            data.get("summary"),
            json.dumps(payload, ensure_ascii=False),
            "pending",
            now,
        ))

    _audit(data["operator"], data.get("device_id"),
           "manual_input", "manual_records", rid,
           {"form_id": data["form_id"], "summary": data.get("summary")})
    return {"id": rid, "submitted_at": now}


def get_manual_records(sync_status: str | None = None, limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        if sync_status:
            rows = conn.execute(
                "SELECT * FROM manual_records WHERE sync_status=? ORDER BY submitted_at DESC LIMIT ?",
                (sync_status, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM manual_records ORDER BY submitted_at DESC LIMIT ?",
                (limit,)).fetchall()
    result = []
    for r in rows:
        d = _row_to_dict(r)
        if d.get("payload") and isinstance(d["payload"], str):
            try:
                d["payload"] = json.loads(d["payload"])
            except Exception:
                pass
        result.append(d)
    return result


def mark_manual_record_synced(record_id: str, operator: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE manual_records SET sync_status='synced', synced_at=? WHERE id=?",
            (_now(), record_id)
        )
    _audit(operator, None, "manual_record_synced", "manual_records", record_id, {})
