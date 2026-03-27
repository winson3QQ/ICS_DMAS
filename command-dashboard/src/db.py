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

DB_PATH = Path(__file__).parent.parent / "data" / "ics.db"


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

-- 計算引擎預測結果（每次新增 SNAPSHOT 後非同步產生）
CREATE TABLE IF NOT EXISTS predictions (
    id              TEXT PRIMARY KEY,   -- UUID
    node_type       TEXT NOT NULL,      -- medical/shelter/forward/security
    metric          TEXT NOT NULL,      -- 預測指標名稱
    current_value   REAL,
    predicted_at    TEXT NOT NULL,      -- 預測產生時間
    eta_threshold   TEXT,              -- 預計到達門檻的時間（ISO UTC），可為 null
    confidence      TEXT NOT NULL DEFAULT 'low',  -- high/medium/low/insufficient
    trend_rate      REAL,              -- 趨勢速率（每分鐘變化量）
    basis_snap_ids  TEXT,              -- JSON array，計算所用的 snapshot_id 列表
    status          TEXT NOT NULL DEFAULT 'active',  -- active/expired
    created_at      TEXT NOT NULL
);

-- 網路恢復同步記錄（三 Pass 對齊執行結果，不可刪除）
CREATE TABLE IF NOT EXISTS sync_log (
    id                  TEXT PRIMARY KEY,   -- UUID
    source_unit         TEXT NOT NULL,      -- shelter/medical/forward/security
    sync_started_at     TEXT NOT NULL,
    sync_completed_at   TEXT,
    data_gap_start      TEXT,              -- 斷線空洞起始時間
    data_gap_end        TEXT,              -- 斷線空洞結束時間
    pass1_merged        INTEGER DEFAULT 0, -- SNAPSHOT 自動合併筆數
    pass2_manual        INTEGER DEFAULT 0, -- 需人工確認筆數
    pass3_added         INTEGER DEFAULT 0, -- 自動新增筆數
    conflicts_manual    INTEGER DEFAULT 0, -- 衝突需人工筆數
    status              TEXT NOT NULL DEFAULT 'in_progress',
        -- in_progress/completed/partial
    triggered_by        TEXT,              -- auto（網路恢復）/ manual
    operator            TEXT,
    detail              TEXT               -- JSON，完整對齊摘要
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
CREATE INDEX IF NOT EXISTS idx_predictions_node_status
    ON predictions(node_type, status, predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_log_unit
    ON sync_log(source_unit, sync_started_at DESC);
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


# ──────────────────────────────────────────
# 三 Pass 對齊（網路恢復後同步）
# ──────────────────────────────────────────

def execute_three_pass(source_unit: str, sync_data: dict,
                       operator: str = "auto") -> dict:
    """
    執行三 Pass 對齊邏輯。

    sync_data keys:
      sync_start_ts   str  斷線起始時間（ISO UTC）
      device_id       str  來源裝置識別
      snapshots       list 含 snapshot_id 的快照列表
      events          list 斷線期間的事件
      manual_records  list 斷線期間的手動輸入記錄

    回傳 sync_log entry dict。
    """
    sync_id   = str(uuid.uuid4())
    now       = _now()
    start_ts  = sync_data.get("sync_start_ts", now)
    device_id = sync_data.get("device_id", "")

    p1_merged  = 0   # Pass 1：自動合併（QR→完整）
    p1_added   = 0   # Pass 1：新增（指揮部無此快照）
    p2_pending = []  # Pass 2：待人工確認衝突
    p3_added   = 0   # Pass 3：直接補傳無衝突記錄

    with get_conn() as conn:

        # ── Pass 1：SNAPSHOT 去重與補齊 ──────────
        # 規格：有 snapshot_id 者自動合併外部完整快照
        for snap in (sync_data.get("snapshots") or []):
            snap_id = snap.get("snapshot_id") or snap.get("snapshot_uuid")
            if not snap_id:
                continue

            existing = conn.execute(
                "SELECT id, source FROM snapshots WHERE snapshot_id=?",
                (snap_id,)
            ).fetchone()

            extra_json = json.dumps(snap.get("extra") or {}, ensure_ascii=False)

            if existing:
                ex_source = existing["source"] if existing else "auto"
                # 若已有 QR 版本 → 以完整記錄覆蓋，更新 source=merged
                new_source = "merged" if ex_source == "qr" else ex_source
                conn.execute("""
                    UPDATE snapshots
                    SET source=?, extra=?,
                        casualties_red=?, casualties_yellow=?,
                        casualties_green=?, casualties_black=?,
                        bed_used=?, bed_total=?,
                        waiting_count=?, pending_evac=?,
                        vehicle_available=?, staff_on_duty=?
                    WHERE snapshot_id=?
                """, (
                    new_source,
                    extra_json,
                    snap.get("casualties_red"),
                    snap.get("casualties_yellow"),
                    snap.get("casualties_green"),
                    snap.get("casualties_black"),
                    snap.get("bed_used"),
                    snap.get("bed_total"),
                    snap.get("waiting_count"),
                    snap.get("pending_evac"),
                    snap.get("vehicle_available"),
                    snap.get("staff_on_duty"),
                    snap_id,
                ))
                p1_merged += 1
            else:
                # 指揮部沒有此快照 → 直接補入，source=sync_recovery
                node_type = snap.get("node_type") or _unit_to_node(source_unit)
                new_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT OR IGNORE INTO snapshots
                        (id, snapshot_id, node_type, source, snapshot_time,
                         casualties_red, casualties_yellow, casualties_green, casualties_black,
                         bed_used, bed_total, waiting_count, pending_evac,
                         vehicle_available, staff_on_duty, extra)
                    VALUES (?,?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?)
                """, (
                    new_id, snap_id, node_type, "sync_recovery",
                    snap.get("t") or snap.get("snapshot_time") or now,
                    snap.get("casualties_red"),
                    snap.get("casualties_yellow"),
                    snap.get("casualties_green"),
                    snap.get("casualties_black"),
                    snap.get("bed_used"),
                    snap.get("bed_total"),
                    snap.get("waiting_count"),
                    snap.get("pending_evac"),
                    snap.get("vehicle_available"),
                    snap.get("staff_on_duty"),
                    extra_json,
                ))
                p1_added += 1

        # ── Pass 2：手動記錄模糊比對 ─────────────
        # 規格：相似度評分後人工確認（離站衝突必須人工）
        for rec in (sync_data.get("manual_records") or []):
            rec_time = rec.get("submitted_at") or rec.get("timestamp") or now
            rec_type = rec.get("form_id") or rec.get("type", "")
            rec_summary = rec.get("summary", "")

            # 查找指揮部是否有相似記錄（相同類型、時間差 ±30 分鐘）
            conflict = conn.execute("""
                SELECT id, summary, submitted_at FROM manual_records
                WHERE form_id=?
                  AND ABS(
                    (julianday(submitted_at) - julianday(?)) * 1440
                  ) < 30
                ORDER BY ABS(julianday(submitted_at) - julianday(?))
                LIMIT 1
            """, (rec_type, rec_time, rec_time)).fetchone()

            if conflict:
                p2_pending.append({
                    "incoming":  {"summary": rec_summary, "time": rec_time, "data": rec},
                    "existing":  _row_to_dict(conflict),
                    "action":    None,   # 等人工決定：keep_incoming / keep_existing / merge
                })
            else:
                # Pass 3：無衝突，直接補入
                new_rid = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO manual_records
                        (id, form_id, form_type, target_table, operator,
                         summary, payload, sync_status, submitted_at)
                    VALUES (?,?,?,?,?, ?,?,?,?)
                """, (
                    new_rid,
                    rec_type,
                    rec.get("form_type", ""),
                    rec.get("target_table", ""),
                    operator,
                    rec_summary,
                    json.dumps(rec.get("payload") or rec, ensure_ascii=False),
                    "synced",
                    rec_time,
                ))
                p3_added += 1

        # ── Pass 3：事件補傳（有時間戳的直接寫入）──
        for ev in (sync_data.get("events") or []):
            ev_id = ev.get("id")
            if ev_id:
                existing_ev = conn.execute(
                    "SELECT id FROM events WHERE id=?", (ev_id,)
                ).fetchone()
                if existing_ev:
                    continue  # 已有，略過

            new_ev_id = ev_id or str(uuid.uuid4())
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO events
                        (id, unit, type, description, severity, status,
                         occurred_at, operator, source)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    new_ev_id,
                    ev.get("unit", source_unit),
                    ev.get("type", "sync_recovery"),
                    ev.get("description", ""),
                    ev.get("severity", "info"),
                    ev.get("status", "open"),
                    ev.get("occurred_at") or ev.get("timestamp") or now,
                    ev.get("operator", operator),
                    "sync_recovery",
                ))
                p3_added += 1
            except Exception:
                pass  # 忽略個別寫入失敗

        # ── 記錄 sync_log ─────────────────────────
        status = "completed" if not p2_pending else "partial"
        detail = json.dumps({
            "pass1_merged": p1_merged,
            "pass1_added":  p1_added,
            "pass2_conflicts": p2_pending,
            "pass3_added":  p3_added,
            "device_id":    device_id,
        }, ensure_ascii=False)

        conn.execute("""
            INSERT INTO sync_log
                (id, source_unit, sync_started_at, sync_completed_at,
                 data_gap_start, data_gap_end,
                 pass1_merged, pass2_manual, pass3_added, conflicts_manual,
                 status, triggered_by, operator, detail)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            sync_id, source_unit, now, now,
            start_ts, now,
            p1_merged, len(p2_pending), p3_added, len(p2_pending),
            status, "api", operator, detail,
        ))

    _audit(operator, device_id, "three_pass_sync", "sync_log", sync_id, {
        "source_unit": source_unit,
        "p1_merged":   p1_merged,
        "p1_added":    p1_added,
        "p2_pending":  len(p2_pending),
        "p3_added":    p3_added,
        "status":      status,
    })

    return {
        "sync_id":     sync_id,
        "status":      status,
        "pass1_merged": p1_merged,
        "pass1_added":  p1_added,
        "pass2_conflicts": len(p2_pending),
        "pass3_added":  p3_added,
        "conflicts":   p2_pending,
    }


def get_sync_log(source_unit: str | None = None, limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        if source_unit:
            rows = conn.execute("""
                SELECT * FROM sync_log
                WHERE source_unit=?
                ORDER BY sync_started_at DESC LIMIT ?
            """, (source_unit, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM sync_log
                ORDER BY sync_started_at DESC LIMIT ?
            """, (limit,)).fetchall()
    result = []
    for r in rows:
        d = _row_to_dict(r)
        if d.get("detail") and isinstance(d["detail"], str):
            try:
                d["detail"] = json.loads(d["detail"])
            except Exception:
                pass
        result.append(d)
    return result


def get_sync_conflicts(sync_id: str) -> dict | None:
    """取得某次同步的 Pass 2 衝突列表"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sync_log WHERE id=?", (sync_id,)
        ).fetchone()
    if not row:
        return None
    d = _row_to_dict(row)
    if isinstance(d.get("detail"), str):
        try:
            d["detail"] = json.loads(d["detail"])
        except Exception:
            pass
    return d


def resolve_conflict(sync_id: str, conflict_idx: int,
                     action: str, operator: str) -> dict:
    """
    解決 Pass 2 衝突。
    action: keep_incoming / keep_existing / merge
    """
    entry = get_sync_conflicts(sync_id)
    if not entry:
        raise ValueError(f"sync_id {sync_id} not found")

    detail = entry.get("detail") or {}
    conflicts = detail.get("pass2_conflicts") or []

    if conflict_idx >= len(conflicts):
        raise ValueError(f"conflict_idx {conflict_idx} out of range")

    conflict = conflicts[conflict_idx]
    conflict["action"] = action
    conflict["resolved_by"] = operator
    conflict["resolved_at"] = _now()

    # 若選擇保留 incoming → 寫入 manual_records
    if action == "keep_incoming":
        rec = conflict.get("incoming", {}).get("data", {})
        new_rid = str(uuid.uuid4())
        now = _now()
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO manual_records
                    (id, form_id, form_type, target_table, operator,
                     summary, payload, sync_status, submitted_at)
                VALUES (?,?,?,?,?, ?,?,?,?)
            """, (
                new_rid,
                rec.get("form_id", rec.get("type", "")),
                rec.get("form_type", ""),
                rec.get("target_table", ""),
                operator,
                conflict["incoming"].get("summary", ""),
                json.dumps(rec, ensure_ascii=False),
                "synced",
                conflict["incoming"].get("time", now),
            ))

    # 更新 detail
    detail["pass2_conflicts"] = conflicts
    all_resolved = all(c.get("action") for c in conflicts)
    new_status = "completed" if all_resolved else "partial"

    with get_conn() as conn:
        conn.execute("""
            UPDATE sync_log SET detail=?, status=? WHERE id=?
        """, (json.dumps(detail, ensure_ascii=False), new_status, sync_id))

    _audit(operator, None, "conflict_resolved", "sync_log", sync_id,
           {"conflict_idx": conflict_idx, "action": action})

    return {"sync_id": sync_id, "conflict_idx": conflict_idx,
            "action": action, "status": new_status}


def _unit_to_node(unit: str) -> str:
    """將 source_unit 轉換為 node_type"""
    return {
        "shelter":  "shelter",
        "medical":  "medical",
        "forward":  "forward",
        "security": "security",
    }.get(unit, unit)
