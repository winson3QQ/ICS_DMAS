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
import hashlib
import os
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
    received_at     TEXT    NOT NULL,          -- 指揮部收到的時間
    session_type    TEXT    NOT NULL DEFAULT 'real'  -- real / exercise
);

-- 事件記錄
CREATE TABLE IF NOT EXISTS events (
    id                      TEXT PRIMARY KEY,  -- UUID
    event_code              TEXT,              -- 可讀編號 EV-MMDD-NNN
    reported_by_unit        TEXT NOT NULL,
    location_desc           TEXT,
    location_zone_id        TEXT,              -- 對應 map_config zone.id（地圖據點）
    event_type              TEXT NOT NULL,
    severity                TEXT NOT NULL DEFAULT 'info',  -- critical/warning/info
    status                  TEXT NOT NULL DEFAULT 'open',  -- open/in_progress/resolved/closed
    response_type           TEXT,
    response_deadline       TEXT,              -- ISO UTC，依嚴重度自動計算的處置期限
    needs_commander_decision INTEGER NOT NULL DEFAULT 0,   -- 0/1
    description             TEXT NOT NULL,
    related_person_name     TEXT,
    assigned_to             TEXT,              -- 負責人
    notes                   TEXT,              -- JSON array [{time, text, by}]
    occurred_at             TEXT NOT NULL,
    resolved_at             TEXT,
    operator_name           TEXT NOT NULL,
    created_at              TEXT NOT NULL,
    session_type            TEXT NOT NULL DEFAULT 'real'  -- real / exercise
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
    created_at          TEXT NOT NULL,
    session_type        TEXT NOT NULL DEFAULT 'real'  -- real / exercise
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
    created_at   TEXT NOT NULL,
    session_type TEXT NOT NULL DEFAULT 'real'  -- real / exercise
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
    synced_at    TEXT,
    session_type TEXT NOT NULL DEFAULT 'real'  -- real / exercise
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
    created_at      TEXT NOT NULL,
    session_type    TEXT NOT NULL DEFAULT 'real'  -- real / exercise
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

-- 帳號管理
CREATE TABLE IF NOT EXISTS accounts (
    username      TEXT PRIMARY KEY,
    pin_hash      TEXT NOT NULL,
    pin_salt      TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT '操作員',   -- 指揮官 / 操作員（粗分，權限控制用）
    role_detail   TEXT,                            -- 細分角色（醫療：檢傷官/治療官/後送官/後勤官/組長；收容：一般/組長）
    display_name  TEXT,
    status        TEXT NOT NULL DEFAULT 'active',  -- active / suspended
    created_at    TEXT NOT NULL,
    updated_at    TEXT
);

-- 系統設定（admin_pin、指揮部名稱等）
CREATE TABLE IF NOT EXISTS config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Wave 4：Pi 節點管理
CREATE TABLE IF NOT EXISTS pi_nodes (
    unit_id      TEXT PRIMARY KEY,           -- 'shelter' / 'medical' / ...
    label        TEXT NOT NULL,              -- 顯示名稱
    api_key      TEXT NOT NULL UNIQUE,       -- Bearer token (hex, 32 bytes)
    last_seen_at TEXT,                       -- 最後一次心跳/推送時間
    last_data_at TEXT,                       -- 最後一次有資料推送時間
    created_at   TEXT NOT NULL,
    revoked_at   TEXT                        -- 非 NULL 代表已撤銷
);

-- Wave 4：Pi 推送接收批次
CREATE TABLE IF NOT EXISTS pi_received_batches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id      TEXT NOT NULL,
    pushed_at    TEXT NOT NULL,              -- Pi 端產生時間
    received_at  TEXT NOT NULL,              -- 指揮部收到時間
    records_json TEXT NOT NULL               -- JSON array of records
);

-- TTX 演練場次
CREATE TABLE IF NOT EXISTS ttx_sessions (
    id              TEXT PRIMARY KEY,
    session_name    TEXT NOT NULL,
    scenario_id     TEXT,
    facilitator     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'setup',
    started_at      TEXT,
    ended_at        TEXT,
    created_at      TEXT NOT NULL,
    session_type    TEXT NOT NULL DEFAULT 'exercise'
);

-- TTX 情境注入卡
CREATE TABLE IF NOT EXISTS ttx_injects (
    id                    TEXT PRIMARY KEY,
    session_id            TEXT NOT NULL REFERENCES ttx_sessions(id),
    inject_seq            INTEGER NOT NULL,
    target_unit           TEXT NOT NULL,
    inject_type           TEXT NOT NULL,
    title                 TEXT NOT NULL,
    description           TEXT,
    payload               TEXT NOT NULL,
    scheduled_offset_min  INTEGER,
    status                TEXT NOT NULL DEFAULT 'pending',
    injected_at           TEXT,
    created_at            TEXT NOT NULL
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_pi_nodes_api_key
    ON pi_nodes(api_key);
CREATE INDEX IF NOT EXISTS idx_pi_received_unit
    ON pi_received_batches(unit_id, received_at DESC);
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_code_unique
    ON events(event_code);
CREATE INDEX IF NOT EXISTS idx_ttx_injects_session
    ON ttx_injects(session_id, inject_seq);
"""


def init_db():
    """建立所有資料表（idempotent）+ seed 預設管理員帳號"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)

    # Seed：若 accounts 空，建立預設 admin/1234（指揮官）
    with get_conn() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
        if cnt == 0:
            pin_hash, pin_salt = _hash_pin("1234")
            now = _now()
            conn.execute(
                """INSERT INTO accounts
                   (username, pin_hash, pin_salt, role, display_name, status, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                ("admin", pin_hash, pin_salt, "指揮官", "系統管理員", "active", now)
            )
            # 同時設定 admin_pin（預設也是 1234）
            adm_hash, adm_salt = _hash_pin("1234")
            conn.execute(
                "INSERT OR IGNORE INTO config (key, value, updated_at) VALUES (?,?,?)",
                ("admin_pin", json.dumps({"hash": adm_hash, "salt": adm_salt}), now)
            )
            # audit 寫在同一 connection 內避免 DB locked
            conn.execute(
                """INSERT INTO audit_log
                   (operator, device_id, action_type, target_table, target_id, detail, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                ("system", None, "account_created", "accounts", "admin",
                 json.dumps({"role": "指揮官", "note": "首次啟動自動建立預設帳號 admin/1234"}, ensure_ascii=False),
                 now)
            )


# ──────────────────────────────────────────
# SNAPSHOT CRUD
# ──────────────────────────────────────────

def upsert_snapshot(data: dict, session_type: str = "real") -> dict:
    """
    寫入一筆快照。若 snapshot_id 已存在則忽略（idempotent）。
    回傳 {inserted: bool, id: int}
    """
    now = _now()
    extra = data.get("extra") or {}

    # 從頂層搬到 extra（僅當頂層有實際值時才覆寫，避免 Pydantic None 蓋掉 extra 原有值）
    for key in ("supplies", "units", "srt", "pending_intake", "cmist_pending",
                "post_total", "post_anomaly", "qrf_available", "isolation_count"):
        if data.get(key) is not None:
            extra[key] = data[key]

    sql = """
        INSERT OR IGNORE INTO snapshots
            (snapshot_id, snapshot_time, node_type, source,
             casualties_red, casualties_yellow, casualties_green, casualties_black,
             bed_used, bed_total, waiting_count, pending_evac,
             vehicle_available, staff_on_duty, extra, received_at, session_type)
        VALUES
            (?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?, ?,?)
    """
    casualties = data.get("casualties") or {}
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
            session_type,
        ))
        inserted = cur.rowcount > 0
        row_id   = cur.lastrowid if inserted else None

    _audit("system", None, "snapshot_received",
           "snapshots", data["snapshot_id"],
           {"node_type": data["node_type"], "source": data.get("source","auto"), "inserted": inserted},
           session_type=session_type)

    return {"inserted": inserted, "snapshot_id": data["snapshot_id"]}


def get_snapshots(node_type: str, limit: int = 20, session_type: str = "real") -> list[dict]:
    """取最近 N 筆快照（依 snapshot_time 倒序）"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE node_type=? AND session_type=? ORDER BY snapshot_time DESC LIMIT ?",
            (node_type, session_type, limit)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_latest_snapshot(node_type: str, session_type: str = "real") -> dict | None:
    rows = get_snapshots(node_type, limit=1, session_type=session_type)
    return rows[0] if rows else None


# ──────────────────────────────────────────
# EVENT CRUD
# ──────────────────────────────────────────

def create_event(data: dict, session_type: str = "real") -> dict:
    eid = str(uuid.uuid4())
    now = _now()
    severity = data.get("severity", "info")

    # 依嚴重度計算處置期限（critical=10分/warning=30分/info=60分）
    deadline_min = {"critical": 10, "warning": 30, "info": 60}.get(severity, 60)
    occurred = data.get("occurred_at") or now
    response_deadline = _add_minutes(occurred, deadline_min)

    mmdd = now[5:7] + now[8:10]
    prefix = f"EV-{mmdd}-"

    # event_code 用 subquery 在 INSERT 內原子產生，
    # 搭配 UNIQUE INDEX + retry 防止併發重號。
    sql = """
        INSERT INTO events
            (id, event_code, reported_by_unit, location_desc, location_zone_id,
             event_type, severity, status, response_type, response_deadline,
             needs_commander_decision, description,
             related_person_name, occurred_at, operator_name, created_at, session_type)
        VALUES (?,
            (SELECT ? || printf('%03d',
                COALESCE(MAX(CAST(SUBSTR(event_code, -3) AS INTEGER)), 0) + 1)
             FROM events WHERE event_code LIKE ?),
            ?,?,?, ?,?,?,?, ?,?, ?,?,?,?,?,?)
    """

    max_retries = 10
    for attempt in range(max_retries):
        try:
            with get_conn() as conn:
                conn.execute(sql, (
                    eid,
                    prefix, prefix + "%",
                    data["reported_by_unit"],
                    data.get("location_desc"),
                    data.get("location_zone_id"),
                    data["event_type"],
                    severity,
                    "open",
                    data.get("response_type"),
                    response_deadline,
                    1 if data.get("needs_commander_decision") else 0,
                    data["description"],
                    data.get("related_person_name"),
                    occurred,
                    data["operator_name"],
                    now,
                    session_type,
                ))
                # 取回實際產生的 event_code
                row = conn.execute("SELECT event_code FROM events WHERE id=?", (eid,)).fetchone()
                event_code = row["event_code"]
            break
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) and attempt < max_retries - 1:
                import time as _t
                _t.sleep(0.01 * (attempt + 1))
                eid = str(uuid.uuid4())
                continue
            raise

    _audit(data["operator_name"], None, "event_created",
           "events", eid, {"event_code": event_code, "event_type": data["event_type"], "severity": severity},
           session_type=session_type)
    return {"id": eid, "event_code": event_code, "response_deadline": response_deadline}


def _add_minutes(iso_str: str, minutes: int) -> str:
    """ISO UTC 字串加 N 分鐘"""
    from datetime import timedelta
    dt_str = iso_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(dt_str)
    result = dt + timedelta(minutes=minutes)
    return result.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_events(status: str | None = None, limit: int = 50, session_type: str = "real") -> list[dict]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM events WHERE status=? AND session_type=? ORDER BY occurred_at DESC LIMIT ?",
                (status, session_type, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events WHERE session_type=? ORDER BY occurred_at DESC LIMIT ?",
                (session_type, limit)).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_event_status(event_id: str, status: str, operator: str, session_type: str = "real"):
    """更新事件狀態，含狀態機防護 + json_insert 原子追加 notes"""
    valid_transitions = {
        "open":        {"in_progress", "resolved", "closed"},
        "in_progress": {"in_progress", "resolved", "closed"},
        "resolved":    set(),
        "closed":      set(),
    }

    now = _now()
    status_label = {"open":"未結","in_progress":"處理中","resolved":"已結案","closed":"已關閉"}.get(status, status)
    note_json = json.dumps({"time": now, "text": f"狀態變更為「{status_label}」", "by": operator}, ensure_ascii=False)

    with get_conn() as conn:
        row = conn.execute("SELECT status FROM events WHERE id=? AND session_type=?", (event_id, session_type)).fetchone()
        if not row:
            raise ValueError(f"事件 {event_id} 不存在")
        current = row["status"]
        allowed = valid_transitions.get(current, set())
        if status not in allowed:
            raise ValueError(f"不允許從「{current}」轉換到「{status}」")

        if status in ("resolved", "closed"):
            conn.execute(
                """UPDATE events SET status=?, resolved_at=?,
                   notes = json_insert(COALESCE(notes, '[]'), '$[#]', json(?))
                   WHERE id=? AND session_type=?""",
                (status, now, note_json, event_id, session_type)
            )
        else:
            conn.execute(
                """UPDATE events SET status=?,
                   notes = json_insert(COALESCE(notes, '[]'), '$[#]', json(?))
                   WHERE id=? AND session_type=?""",
                (status, note_json, event_id, session_type)
            )
    _audit(operator, None, "event_status_updated", "events", event_id, {"status": status},
           session_type=session_type)


def add_event_note(event_id: str, text: str, operator: str, session_type: str = "real") -> dict:
    """追加處置紀錄，使用 json_insert 原子操作避免併發覆蓋"""
    now = _now()
    note_json = json.dumps({"time": now, "text": text, "by": operator}, ensure_ascii=False)
    with get_conn() as conn:
        row = conn.execute("SELECT status FROM events WHERE id=? AND session_type=?", (event_id, session_type)).fetchone()
        if not row:
            raise ValueError(f"Event {event_id} not found")
        # 追加紀錄時自動改為「處理中」
        new_status = "in_progress" if row["status"] == "open" else row["status"]
        conn.execute(
            """UPDATE events SET
               notes = json_insert(COALESCE(notes, '[]'), '$[#]', json(?)),
               status = ?
               WHERE id = ? AND session_type=?""",
            (note_json, new_status, event_id, session_type)
        )
        cnt_row = conn.execute(
            "SELECT json_array_length(COALESCE(notes, '[]')) as cnt FROM events WHERE id=? AND session_type=?",
            (event_id, session_type)
        ).fetchone()
    _audit(operator, None, "event_note_added", "events", event_id,
           {"text": text[:50]},
           session_type=session_type)
    return {"ok": True, "notes_count": cnt_row["cnt"] if cnt_row else 0}


# ──────────────────────────────────────────
# DECISION CRUD
# ──────────────────────────────────────────

def create_decision(data: dict, session_type: str = "real") -> dict:
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
                "(id=? OR parent_decision_id=?) AND session_type=?",
                (data["parent_decision_id"], data["parent_decision_id"], session_type)
            ).fetchone()
        seq = (rows["cnt"] or 0) + 2

    sql = """
        INSERT INTO decisions
            (id, primary_event_id, decision_seq, parent_decision_id,
             decision_type, severity, decision_title, impact_description,
             suggested_action_a, suggested_action_b, status,
             created_by, created_at, session_type)
        VALUES (?,?,?,?, ?,?,?,?, ?,?,?, ?,?,?)
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
            session_type,
        ))
        # 若有 parent，將上一筆標記為 superseded
        if data.get("parent_decision_id"):
            conn.execute(
                "UPDATE decisions SET status='superseded', superseded_by=? WHERE id=? AND session_type=?",
                (did, data["parent_decision_id"], session_type)
            )

    _audit(data["created_by"], None, "decision_created", "decisions", did,
           {"title": data["decision_title"], "severity": data["severity"],
            "type": data["decision_type"]},
           session_type=session_type)
    return {"id": did}


def decide(decision_id: str, action: str, decided_by: str, execution_note: str = "",
           session_type: str = "real") -> dict:
    """
    action: approved / hold / redirect / completed
    Write-Freeze 後不可再修改（除非是 closure 新增一筆）
    """
    valid_actions = {"approved", "hold", "redirect", "completed"}
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}")

    now = _now()
    with get_conn() as conn:
        row = conn.execute("SELECT status FROM decisions WHERE id=? AND session_type=?", (decision_id, session_type)).fetchone()
        if not row:
            raise ValueError("Decision not found")
        if row["status"] not in ("pending",):
            raise ValueError(f"Decision already decided: {row['status']}")
        conn.execute(
            "UPDATE decisions SET status=?, decided_by=?, decided_at=?, execution_note=? WHERE id=? AND session_type=?",
            (action, decided_by, now, execution_note, decision_id, session_type)
        )

    _audit(decided_by, None, "decision_made", "decisions", decision_id,
           {"action": action, "execution_note": execution_note},
           session_type=session_type)
    return {"id": decision_id, "status": action, "decided_at": now}


def get_decisions(status: str | None = None, session_type: str = "real") -> list[dict]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE status=? AND session_type=? ORDER BY created_at DESC",
                (status, session_type)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE session_type=? ORDER BY created_at DESC",
                (session_type,)).fetchall()
    return [_row_to_dict(r) for r in rows]


# ──────────────────────────────────────────
# AUDIT LOG（只寫，不讀）
# ──────────────────────────────────────────

def _audit(operator: str, device_id: str | None,
           action_type: str, target_table: str, target_id: str, detail: dict,
           session_type: str = "real"):
    sql = """
        INSERT INTO audit_log
            (operator, device_id, action_type, target_table, target_id, detail, created_at, session_type)
        VALUES (?,?,?,?,?,?,?,?)
    """
    with get_conn() as conn:
        conn.execute(sql, (
            operator, device_id, action_type,
            target_table, str(target_id),
            json.dumps(detail, ensure_ascii=False),
            _now(),
            session_type,
        ))


def get_audit_log(limit: int = 100, session_type: str = "real") -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT a.*,
                   e.event_code  AS _event_code,
                   e.description AS _event_desc
            FROM   audit_log a
            LEFT JOIN events e
                ON  a.target_table = 'events'
                AND a.target_id    = e.id
            WHERE  a.session_type = ?
            ORDER  BY a.created_at DESC
            LIMIT  ?
        """, (session_type, limit)).fetchall()
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

def create_manual_record(data: dict, session_type: str = "real") -> dict:
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
             summary, payload, sync_status, submitted_at, session_type)
        VALUES (?,?,?,?,?, ?,?,?,?,?)
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
            session_type,
        ))

    _audit(data["operator"], data.get("device_id"),
           "manual_input", "manual_records", rid,
           {"form_id": data["form_id"], "summary": data.get("summary")},
           session_type=session_type)
    return {"id": rid, "submitted_at": now}


def get_manual_records(sync_status: str | None = None, limit: int = 100, session_type: str = "real") -> list[dict]:
    with get_conn() as conn:
        if sync_status:
            rows = conn.execute(
                "SELECT * FROM manual_records WHERE sync_status=? AND session_type=? ORDER BY submitted_at DESC LIMIT ?",
                (sync_status, session_type, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM manual_records WHERE session_type=? ORDER BY submitted_at DESC LIMIT ?",
                (session_type, limit)).fetchall()
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


def mark_manual_record_synced(record_id: str, operator: str, session_type: str = "real"):
    with get_conn() as conn:
        conn.execute(
            "UPDATE manual_records SET sync_status='synced', synced_at=? WHERE id=? AND session_type=?",
            (_now(), record_id, session_type)
        )
    _audit(operator, None, "manual_record_synced", "manual_records", record_id, {},
           session_type=session_type)


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

            casualties = snap.get("casualties") or {}

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
                    casualties.get("red")   or snap.get("casualties_red"),
                    casualties.get("yellow")or snap.get("casualties_yellow"),
                    casualties.get("green") or snap.get("casualties_green"),
                    casualties.get("black") or snap.get("casualties_black"),
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
                casualties = snap.get("casualties") or {}
                conn.execute("""
                    INSERT OR IGNORE INTO snapshots
                        (snapshot_id, node_type, source, snapshot_time,
                         casualties_red, casualties_yellow, casualties_green, casualties_black,
                         bed_used, bed_total, waiting_count, pending_evac,
                         vehicle_available, staff_on_duty, extra, received_at)
                    VALUES (?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?,?)
                """, (
                    snap_id, node_type, "sync_recovery",
                    snap.get("t") or snap.get("snapshot_time") or now,
                    casualties.get("red")   or snap.get("casualties_red"),
                    casualties.get("yellow")or snap.get("casualties_yellow"),
                    casualties.get("green") or snap.get("casualties_green"),
                    casualties.get("black") or snap.get("casualties_black"),
                    snap.get("bed_used"),
                    snap.get("bed_total"),
                    snap.get("waiting_count"),
                    snap.get("pending_evac"),
                    snap.get("vehicle_available"),
                    snap.get("staff_on_duty"),
                    extra_json,
                    now,
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


# ──────────────────────────────────────────
# PIN hashing（PBKDF2-SHA256, 100k iterations）
# ──────────────────────────────────────────

def _hash_pin(pin: str, salt_hex: str | None = None) -> tuple[str, str]:
    """雜湊 PIN，回傳 (hash_hex, salt_hex)"""
    if salt_hex is None:
        salt = os.urandom(16)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)
    h = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100_000)
    return h.hex(), salt_hex


def _verify_pin(pin: str, stored_hash: str, stored_salt: str) -> bool:
    """驗證 PIN 是否正確"""
    h, _ = _hash_pin(pin, stored_salt)
    return h == stored_hash


# ──────────────────────────────────────────
# ACCOUNTS CRUD
# ──────────────────────────────────────────

def create_account(username: str, pin: str, role: str = "操作員",
                   display_name: str | None = None,
                   role_detail: str | None = None) -> dict:
    pin_hash, pin_salt = _hash_pin(pin)
    now = _now()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO accounts
               (username, pin_hash, pin_salt, role, role_detail, display_name, status, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (username, pin_hash, pin_salt, role, role_detail, display_name, "active", now)
        )
    _audit("admin", None, "account_created", "accounts", username,
           {"role": role, "role_detail": role_detail})
    return {"username": username, "role": role, "role_detail": role_detail,
            "status": "active", "created_at": now}


def get_all_accounts() -> list[dict]:
    """列出所有帳號（不含 pin_hash/pin_salt）"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT username, role, role_detail, display_name, status, created_at, updated_at "
            "FROM accounts ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def update_account_status(username: str, status: str, operator: str) -> bool:
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET status=?, updated_at=? WHERE username=?",
            (status, now, username)
        )
    if cur.rowcount:
        _audit(operator, None, "account_status_updated", "accounts", username,
               {"status": status})
    return cur.rowcount > 0


def update_account_pin(username: str, new_pin: str, operator: str) -> bool:
    pin_hash, pin_salt = _hash_pin(new_pin)
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET pin_hash=?, pin_salt=?, updated_at=? WHERE username=?",
            (pin_hash, pin_salt, now, username)
        )
    if cur.rowcount:
        _audit(operator, None, "account_pin_reset", "accounts", username, {})
    return cur.rowcount > 0


def update_account_role(username: str, role: str, operator: str,
                        role_detail: str | None = None) -> bool:
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET role=?, role_detail=?, updated_at=? WHERE username=?",
            (role, role_detail, now, username)
        )
    if cur.rowcount:
        _audit(operator, None, "account_role_updated", "accounts", username,
               {"role": role, "role_detail": role_detail})
    return cur.rowcount > 0


def delete_account(username: str, operator: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM accounts WHERE username=?", (username,))
    if cur.rowcount:
        _audit(operator, None, "account_deleted", "accounts", username, {})
    return cur.rowcount > 0


def suspend_all_accounts(operator: str) -> int:
    """緊急：停用所有帳號"""
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE accounts SET status='suspended', updated_at=? WHERE status='active'",
            (now,)
        )
    if cur.rowcount:
        _audit(operator, None, "all_accounts_suspended", "accounts", "*",
               {"count": cur.rowcount})
    return cur.rowcount


def verify_login(username: str, pin: str) -> dict | None:
    """驗證帳密，成功回傳帳號資訊（不含 hash/salt），失敗回傳 None"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE username=?", (username,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    if d["status"] != "active":
        return None
    if not _verify_pin(pin, d["pin_hash"], d["pin_salt"]):
        return None
    # 回傳時移除敏感欄位
    d.pop("pin_hash", None)
    d.pop("pin_salt", None)
    return d


# ──────────────────────────────────────────
# CONFIG CRUD
# ──────────────────────────────────────────

def get_config(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_config(key: str, value: str, operator: str | None = None):
    now = _now()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO config (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, now)
        )
    if operator:
        _audit(operator, None, "config_updated", "config", key, {"value": value})


def verify_admin_pin(pin: str) -> bool:
    """驗證 Admin PIN"""
    raw = get_config("admin_pin")
    if not raw:
        return False
    data = json.loads(raw)
    return _verify_pin(pin, data["hash"], data["salt"])


def set_admin_pin(new_pin: str, operator: str):
    """設定 Admin PIN"""
    h, s = _hash_pin(new_pin)
    set_config("admin_pin", json.dumps({"hash": h, "salt": s}), operator)


# ──────────────────────────────────────────
# Wave 4：PI NODES CRUD
# ──────────────────────────────────────────

import secrets


def create_pi_node(unit_id: str, label: str) -> dict:
    """註冊 Pi 節點，產生 API key。unit_id 重複會拋 IntegrityError。"""
    api_key = secrets.token_hex(32)
    now = _now()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO pi_nodes (unit_id, label, api_key, created_at)
               VALUES (?,?,?,?)""",
            (unit_id, label, api_key, now)
        )
    _audit("admin", None, "pi_node_created", "pi_nodes", unit_id,
           {"label": label})
    return {"unit_id": unit_id, "label": label, "api_key": api_key, "created_at": now}


def list_pi_nodes() -> list[dict]:
    """列出所有 Pi 節點（api_key 只回傳末 8 碼）"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT unit_id, label, api_key, last_seen_at, last_data_at, created_at, revoked_at FROM pi_nodes"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["api_key_suffix"] = d.pop("api_key")[-8:]
        result.append(d)
    return result


def delete_pi_node(unit_id: str) -> bool:
    """刪除 Pi 節點"""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM pi_nodes WHERE unit_id=?", (unit_id,))
    if cur.rowcount:
        _audit("admin", None, "pi_node_deleted", "pi_nodes", unit_id, {})
    return cur.rowcount > 0


def revoke_pi_node_key(unit_id: str) -> dict | None:
    """重新產生 API key（舊 key 立即失效）"""
    new_key = secrets.token_hex(32)
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE pi_nodes SET api_key=?, revoked_at=NULL, last_seen_at=NULL WHERE unit_id=?",
            (new_key, unit_id)
        )
    if cur.rowcount == 0:
        return None
    _audit("admin", None, "pi_node_rekeyed", "pi_nodes", unit_id, {})
    return {"unit_id": unit_id, "api_key": new_key}


def validate_pi_push(unit_id: str, bearer_token: str) -> bool:
    """驗證 Pi push 的 Bearer token 是否匹配且未撤銷"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM pi_nodes WHERE unit_id=? AND api_key=? AND revoked_at IS NULL",
            (unit_id, bearer_token)
        ).fetchone()
    return row is not None


def touch_pi_node(unit_id: str):
    """更新 Pi 節點的 last_seen_at（心跳）"""
    now = _now()
    with get_conn() as conn:
        conn.execute(
            "UPDATE pi_nodes SET last_seen_at=? WHERE unit_id=?",
            (now, unit_id)
        )


def touch_pi_node_data(unit_id: str):
    """更新 Pi 節點的 last_seen_at + last_data_at（有資料推送）"""
    now = _now()
    with get_conn() as conn:
        conn.execute(
            "UPDATE pi_nodes SET last_seen_at=?, last_data_at=? WHERE unit_id=?",
            (now, now, unit_id)
        )


# ──────────────────────────────────────────
# Wave 4：PI RECEIVED BATCHES
# ──────────────────────────────────────────

def insert_pi_batch(unit_id: str, pushed_at: str, records_json: str) -> int:
    """寫入一筆 Pi 推送批次，回傳 batch id"""
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO pi_received_batches (unit_id, pushed_at, received_at, records_json)
               VALUES (?,?,?,?)""",
            (unit_id, pushed_at, now, records_json)
        )
    touch_pi_node_data(unit_id)
    return cur.lastrowid


def get_latest_pi_batch(unit_id: str) -> dict | None:
    """取得某組最新一筆推送批次"""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT id, unit_id, pushed_at, received_at, records_json
               FROM pi_received_batches
               WHERE unit_id=?
               ORDER BY received_at DESC LIMIT 1""",
            (unit_id,)
        ).fetchone()
    return dict(row) if row else None


def get_recent_pi_batches(unit_id: str, limit: int = 40) -> list[dict]:
    """取得某組最近 N 筆推送批次（供趨勢分析用）"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, unit_id, pushed_at, received_at, records_json
               FROM pi_received_batches
               WHERE unit_id=?
               ORDER BY received_at DESC LIMIT ?""",
            (unit_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ── TTX 演練管理 ──

def create_ttx_session(name: str, facilitator: str, scenario_id: str | None = None) -> dict:
    """建立演練場次"""
    sid = str(uuid.uuid4())
    now = _now()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO ttx_sessions
               (id, session_name, scenario_id, facilitator, status, created_at, session_type)
               VALUES (?,?,?,?,?,?,?)""",
            (sid, name, scenario_id, facilitator, "setup", now, "exercise")
        )
    _audit(facilitator, None, "ttx_session_created", "ttx_sessions", sid,
           {"name": name, "scenario_id": scenario_id}, session_type="exercise")
    return {"id": sid, "session_name": name, "scenario_id": scenario_id,
            "facilitator": facilitator, "status": "setup", "created_at": now}


def get_ttx_session(session_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM ttx_sessions WHERE id=?", (session_id,)).fetchone()
    return dict(row) if row else None


def list_ttx_sessions() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM ttx_sessions ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_ttx_session_status(session_id: str, status: str, facilitator: str) -> bool:
    now = _now()
    updates = {"status": status, "updated_fields": {}}
    if status == "running":
        updates["updated_fields"]["started_at"] = now
        sql = "UPDATE ttx_sessions SET status=?, started_at=? WHERE id=?"
        params = (status, now, session_id)
    elif status == "completed":
        updates["updated_fields"]["ended_at"] = now
        sql = "UPDATE ttx_sessions SET status=?, ended_at=? WHERE id=?"
        params = (status, now, session_id)
    else:
        sql = "UPDATE ttx_sessions SET status=? WHERE id=?"
        params = (status, session_id)
    with get_conn() as conn:
        cur = conn.execute(sql, params)
    if cur.rowcount:
        _audit(facilitator, None, "ttx_session_status", "ttx_sessions", session_id,
               updates, session_type="exercise")
    return cur.rowcount > 0


def create_ttx_inject(session_id: str, seq: int, target_unit: str,
                      inject_type: str, title: str, payload: dict,
                      description: str | None = None,
                      scheduled_offset_min: int | None = None) -> dict:
    iid = str(uuid.uuid4())
    now = _now()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO ttx_injects
               (id, session_id, inject_seq, target_unit, inject_type, title,
                description, payload, scheduled_offset_min, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (iid, session_id, seq, target_unit, inject_type, title,
             description, json.dumps(payload, ensure_ascii=False),
             scheduled_offset_min, "pending", now)
        )
    return {"id": iid, "session_id": session_id, "inject_seq": seq,
            "target_unit": target_unit, "inject_type": inject_type,
            "title": title, "status": "pending", "created_at": now}


def bulk_create_ttx_injects(session_id: str, injects: list[dict]) -> int:
    """批次建立 injects，回傳成功筆數"""
    count = 0
    for inj in injects:
        create_ttx_inject(
            session_id=session_id,
            seq=inj["seq"],
            target_unit=inj["target_unit"],
            inject_type=inj["type"],
            title=inj["title"],
            payload=inj["payload"],
            description=inj.get("description"),
            scheduled_offset_min=inj.get("offset_min"),
        )
        count += 1
    return count


def get_ttx_injects(session_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM ttx_injects WHERE session_id=? ORDER BY inject_seq",
            (session_id,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("payload"), str):
            try:
                d["payload"] = json.loads(d["payload"])
            except Exception:
                pass
        result.append(d)
    return result


def mark_ttx_inject_done(inject_id: str, facilitator: str) -> bool:
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE ttx_injects SET status='injected', injected_at=? WHERE id=? AND status='pending'",
            (now, inject_id)
        )
    if cur.rowcount:
        _audit(facilitator, None, "ttx_inject_pushed", "ttx_injects", inject_id,
               {}, session_type="exercise")
    return cur.rowcount > 0
