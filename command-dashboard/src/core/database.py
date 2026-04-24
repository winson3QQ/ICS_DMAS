"""
core/database.py — SQLite 連線管理與 schema 初始化
"""

import sqlite3
from typing import Generator
from .config import DB_PATH


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI Depends 使用"""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """建立所有資料表（idempotent）"""
    conn = get_conn()
    try:
        _create_tables(conn)
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Schema 定義
# ─────────────────────────────────────────────────────────────────────────────

def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    -- ── 既有表（保留相容，migration 補欄位）────────────────────────────────

    CREATE TABLE IF NOT EXISTS snapshots (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id         TEXT UNIQUE NOT NULL,
        snapshot_time       TEXT NOT NULL,
        node_type           TEXT NOT NULL,
        source              TEXT DEFAULT 'auto',
        casualties_red      INTEGER,
        casualties_yellow   INTEGER,
        casualties_green    INTEGER,
        casualties_black    INTEGER,
        bed_used            INTEGER,
        bed_total           INTEGER,
        waiting_count       INTEGER,
        pending_evac        INTEGER,
        vehicle_available   INTEGER,
        staff_on_duty       INTEGER,
        extra               TEXT,
        received_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        exercise_id         INTEGER REFERENCES exercises(id)
    );

    CREATE TABLE IF NOT EXISTS events (
        id                       TEXT PRIMARY KEY,
        event_code               TEXT UNIQUE,
        reported_by_unit         TEXT NOT NULL,
        location_desc            TEXT,
        location_zone_id         TEXT,
        event_type               TEXT NOT NULL,
        severity                 TEXT DEFAULT 'info',
        status                   TEXT DEFAULT 'open',
        response_type            TEXT,
        response_deadline        TEXT,
        needs_commander_decision INTEGER DEFAULT 0,
        description              TEXT,
        related_person_name      TEXT,
        assigned_unit            TEXT,
        occurred_at              TEXT,
        operator_name            TEXT,
        notes                    TEXT,
        resolved_at              TEXT,
        created_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        exercise_id              INTEGER REFERENCES exercises(id),
        event_type_id            INTEGER REFERENCES event_types(id),
        acknowledged_at          TEXT,
        resolution_notes         TEXT
    );

    CREATE TABLE IF NOT EXISTS decisions (
        id                 TEXT PRIMARY KEY,
        primary_event_id   TEXT,
        decision_seq       INTEGER DEFAULT 1,
        parent_decision_id TEXT,
        superseded_by      TEXT,
        decision_type      TEXT NOT NULL,
        severity           TEXT NOT NULL,
        decision_title     TEXT NOT NULL,
        impact_description TEXT NOT NULL,
        suggested_action_a TEXT NOT NULL,
        suggested_action_b TEXT,
        status             TEXT DEFAULT 'pending',
        decided_by         TEXT,
        decided_at         TEXT,
        execution_note     TEXT,
        created_by         TEXT NOT NULL,
        created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        exercise_id        INTEGER REFERENCES exercises(id),
        decision_type_v2   TEXT,
        rationale          TEXT,
        affected_units     TEXT,
        outcome_at         TEXT,
        outcome_notes_ext  TEXT
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        operator     TEXT,
        device_id    TEXT,
        action_type  TEXT NOT NULL,
        target_table TEXT,
        target_id    TEXT,
        detail       TEXT,
        exercise_id  INTEGER REFERENCES exercises(id),
        created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS manual_records (
        id           TEXT PRIMARY KEY,
        form_id      TEXT NOT NULL,
        form_type    TEXT,
        target_table TEXT,
        operator     TEXT NOT NULL,
        summary      TEXT,
        payload      TEXT,
        sync_status  TEXT DEFAULT 'pending',
        submitted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        synced_at    TEXT,
        exercise_id  INTEGER REFERENCES exercises(id)
    );

    CREATE TABLE IF NOT EXISTS predictions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        unit        TEXT NOT NULL,
        data        TEXT NOT NULL,
        created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS sync_log (
        id                 TEXT PRIMARY KEY,
        source_unit        TEXT NOT NULL,
        sync_started_at    TEXT NOT NULL,
        sync_completed_at  TEXT,
        data_gap_start     TEXT,
        data_gap_end       TEXT,
        pass1_merged       INTEGER DEFAULT 0,
        pass2_manual       INTEGER DEFAULT 0,
        pass3_added        INTEGER DEFAULT 0,
        conflicts_manual   INTEGER DEFAULT 0,
        status             TEXT NOT NULL DEFAULT 'pending',
        triggered_by       TEXT,
        operator           TEXT,
        detail             TEXT,
        created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS accounts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        username     TEXT UNIQUE NOT NULL,
        role         TEXT NOT NULL DEFAULT '操作員',
        role_detail  TEXT,
        display_name TEXT,
        status       TEXT NOT NULL DEFAULT 'active',
        pin_hash     TEXT NOT NULL,
        pin_salt     TEXT NOT NULL,
        created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        updated_at   TEXT,
        last_login   TEXT
    );

    CREATE TABLE IF NOT EXISTS config (
        key         TEXT PRIMARY KEY,
        value       TEXT,
        updated_by  TEXT,
        updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS pi_nodes (
        unit_id      TEXT PRIMARY KEY,
        label        TEXT NOT NULL,
        api_key      TEXT NOT NULL,
        last_seen_at TEXT,
        last_data_at TEXT,
        created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        revoked_at   TEXT
    );

    CREATE TABLE IF NOT EXISTS pi_received_batches (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id      TEXT NOT NULL,
        pushed_at    TEXT NOT NULL,
        received_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        records_json TEXT NOT NULL
    );

    -- ── ttx_injects（session_id 欄位舊版，migration 改名） ────────────────

    CREATE TABLE IF NOT EXISTS ttx_injects (
        id                  TEXT PRIMARY KEY,
        exercise_id         INTEGER REFERENCES exercises(id),
        inject_seq          INTEGER NOT NULL,
        target_unit         TEXT NOT NULL,
        inject_type         TEXT NOT NULL,
        title               TEXT NOT NULL,
        description         TEXT,
        payload             TEXT,
        scheduled_offset_min INTEGER DEFAULT 0,
        status              TEXT DEFAULT 'pending',
        injected_at         TEXT,
        signature           TEXT,
        created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    -- ── C0 新表 ───────────────────────────────────────────────────────────

    CREATE TABLE IF NOT EXISTS exercises (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        name               TEXT NOT NULL,
        date               TEXT,
        location           TEXT,
        type               TEXT NOT NULL DEFAULT 'ttx',  -- 'real' | 'ttx'
        scenario_summary   TEXT,
        weather            TEXT,
        participant_count  INTEGER,
        organizing_body    TEXT,
        status             TEXT NOT NULL DEFAULT 'setup', -- 'setup'|'active'|'archived'
        started_at         TEXT,
        ended_at           TEXT,
        -- TTX 專屬（type='real' 時為 NULL）
        facilitator        TEXT,
        scenario_id        TEXT,
        -- C5 前向相容
        mutex_locked       INTEGER NOT NULL DEFAULT 0,  -- 1 = 有 active exercise，不可並行
        created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS event_types (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        code             TEXT UNIQUE NOT NULL,
        name_zh          TEXT NOT NULL,
        category         TEXT NOT NULL,
        default_severity TEXT DEFAULT 'medium'
    );

    CREATE TABLE IF NOT EXISTS resource_snapshots (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        exercise_id    INTEGER REFERENCES exercises(id),
        unit_type      TEXT NOT NULL,
        snapshot_at    TEXT NOT NULL,
        total_beds     INTEGER,
        occupied_beds  INTEGER,
        light_count    INTEGER,
        medium_count   INTEGER,
        severe_count   INTEGER,
        deceased_count INTEGER,
        source         TEXT NOT NULL DEFAULT 'pi_push'
    );

    CREATE TABLE IF NOT EXISTS aar_entries (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        exercise_id INTEGER REFERENCES exercises(id),
        category    TEXT NOT NULL,  -- 'well'|'improve'|'recommend'
        content     TEXT NOT NULL,
        created_by  TEXT,
        created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS exercise_kpis (
        exercise_id INTEGER NOT NULL REFERENCES exercises(id),
        kpi_key     TEXT NOT NULL,
        kpi_value   REAL,
        computed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        PRIMARY KEY (exercise_id, kpi_key)
    );

    CREATE TABLE IF NOT EXISTS ai_recommendations (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        exercise_id         INTEGER REFERENCES exercises(id),
        made_at             TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        recommendation_type TEXT NOT NULL,
        content             TEXT NOT NULL,
        confidence          REAL,
        accepted            INTEGER,  -- NULL=待決, 1=採納, 0=否決
        related_decision_id INTEGER REFERENCES decisions(id),
        outcome_notes       TEXT
    );

    -- ── RBAC roles（config key）───────────────────────────────────────────
    -- 用 accounts.role 欄位，合法值：
    --   'operator' | 'commander' | 'admin' | 'ttx_orchestrator'

    -- ── Sessions（持久化，server 重啟後仍有效）────────────────────────────
    CREATE TABLE IF NOT EXISTS sessions (
        token        TEXT PRIMARY KEY,
        username     TEXT NOT NULL,
        role         TEXT NOT NULL,
        display_name TEXT,
        last_active  TEXT NOT NULL,
        created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );
    """)


# ─────────────────────────────────────────────────────────────────────────────
# Migration：補欄位（idempotent）
# ─────────────────────────────────────────────────────────────────────────────

def _migrate(conn: sqlite3.Connection) -> None:
    _add_column_if_missing(conn, "events", "exercise_id", "INTEGER REFERENCES exercises(id)")
    _add_column_if_missing(conn, "events", "event_type_id", "INTEGER REFERENCES event_types(id)")
    _add_column_if_missing(conn, "events", "assigned_unit", "TEXT")
    _add_column_if_missing(conn, "events", "acknowledged_at", "TEXT")
    _add_column_if_missing(conn, "events", "resolved_at", "TEXT")
    _add_column_if_missing(conn, "events", "resolution_notes", "TEXT")

    _add_column_if_missing(conn, "decisions", "exercise_id", "INTEGER REFERENCES exercises(id)")
    _add_column_if_missing(conn, "decisions", "made_by", "TEXT")  # 原本就有，冪等
    _add_column_if_missing(conn, "decisions", "decision_type", "TEXT")
    _add_column_if_missing(conn, "decisions", "rationale", "TEXT")
    _add_column_if_missing(conn, "decisions", "affected_units", "TEXT")
    _add_column_if_missing(conn, "decisions", "outcome_at", "TEXT")
    _add_column_if_missing(conn, "decisions", "outcome_notes", "TEXT")

    _add_column_if_missing(conn, "snapshots", "exercise_id", "INTEGER REFERENCES exercises(id)")
    _add_column_if_missing(conn, "manual_records", "exercise_id", "INTEGER REFERENCES exercises(id)")
    _add_column_if_missing(conn, "audit_log", "exercise_id", "INTEGER REFERENCES exercises(id)")

    # ttx_injects：舊版有 session_id TEXT NOT NULL REFERENCES ttx_sessions → 整表重建
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "ttx_injects" in tables:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(ttx_injects)")}
        if "session_id" in cols:
            # 舊版 schema，直接清除後 DROP（1 筆測試資料，已確認可清除）
            conn.execute("DROP TABLE ttx_injects")
            tables.discard("ttx_injects")

    # 舊版 ttx_sessions → 清除
    if "ttx_sessions" in tables:
        conn.execute("DROP TABLE IF EXISTS ttx_sessions")


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
