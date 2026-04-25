"""
tests/integration/test_schema_migrations.py — C1-E schema 版本追蹤測試

驗證：
- schema_migrations 表在 init_db() 後存在且有正確紀錄
- 所有已知 migrations 都已套用
- _migrate() 為 idempotent（重複執行不會新增重複紀錄）
- get_schema_version() 回傳最高版本號
- /api/admin/schema-migrations 端點需 Admin PIN 並回傳正確格式
"""

import pytest
from core.database import get_conn, get_schema_version, init_db, _MIGRATIONS
from repositories.config_repo import set_admin_pin


class TestMigrationsTable:
    def test_schema_migrations_table_exists(self, tmp_db):
        """init_db() 後 schema_migrations 表應存在。"""
        with get_conn() as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        assert "schema_migrations" in tables

    def test_all_migrations_applied(self, tmp_db):
        """所有定義在 _MIGRATIONS 的版本都應已套用。"""
        with get_conn() as conn:
            applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        expected = {v for v, _, _ in _MIGRATIONS}
        assert expected == applied

    def test_migration_records_have_name_and_timestamp(self, tmp_db):
        """每筆 migration 紀錄需有 name 和 applied_at。"""
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
            ).fetchall()
        assert len(rows) == len(_MIGRATIONS)
        for row in rows:
            assert row["name"]       # name 不為空
            assert row["applied_at"] # applied_at 不為空

    def test_get_schema_version_returns_max(self, tmp_db):
        """get_schema_version() 應回傳最高版本號。"""
        expected_max = max(v for v, _, _ in _MIGRATIONS)
        with get_conn() as conn:
            assert get_schema_version(conn) == expected_max

    def test_migrate_is_idempotent(self, tmp_db):
        """重複呼叫 init_db() 不會產生重複 migration 紀錄。"""
        init_db()  # 再跑一次
        with get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        assert count == len(_MIGRATIONS)

    def test_migrations_versions_are_sequential(self, tmp_db):
        """版本號應從 1 開始連續遞增（無跳號）。"""
        versions = sorted(v for v, _, _ in _MIGRATIONS)
        assert versions == list(range(1, len(_MIGRATIONS) + 1))


class TestM006Migration:
    def test_accounts_has_deleted_at(self, tmp_db):
        """M006：accounts 表應有 deleted_at 欄位。"""
        with get_conn() as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(accounts)")}
        assert "deleted_at" in cols

    def test_operational_periods_table_exists(self, tmp_db):
        """M006：operational_periods 表應存在。"""
        with get_conn() as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        assert "operational_periods" in tables

    def test_duty_log_table_exists(self, tmp_db):
        """M006：duty_log 表應存在。"""
        with get_conn() as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        assert "duty_log" in tables

    def test_deleted_at_defaults_null(self, tmp_db):
        """M006：現有帳號的 deleted_at 應為 NULL（不影響舊資料）。"""
        from repositories.account_repo import create_account
        create_account("testuser", "1234", "操作員")
        with get_conn() as conn:
            row = conn.execute(
                "SELECT deleted_at FROM accounts WHERE username='testuser'"
            ).fetchone()
        assert row["deleted_at"] is None


class TestM007Migration:
    def test_admin_role_upgraded_to_sysadmin(self, tmp_db):
        """M007：username='admin' 且 role='指揮官' 的帳號應自動升級為 '系統管理員'。"""
        import sqlite3 as _sqlite3
        # 直接寫入舊版 role（模擬 migration 前的狀態）
        with get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO accounts "
                "(username, pin_hash, pin_salt, role, status, created_at) "
                "VALUES ('admin', 'h', 's', '指揮官', 'active', '2024-01-01T00:00:00Z')"
            )
            conn.commit()
        # 重新執行 _migrate（M007 已在 tmp_db 建立時套用過，需手動模擬未套用狀態）
        # 直接呼叫 migration 函式測試邏輯
        from core.database import _m007_upgrade_admin_role
        with get_conn() as conn:
            _m007_upgrade_admin_role(conn)
            row = conn.execute(
                "SELECT role FROM accounts WHERE username='admin'"
            ).fetchone()
        assert row["role"] == "系統管理員"

    def test_m007_idempotent_on_sysadmin(self, tmp_db):
        """M007：對已是 '系統管理員' 的 admin 帳號重跑不影響。"""
        from repositories.account_repo import create_account
        from core.database import _m007_upgrade_admin_role
        create_account("admin", "1234", "系統管理員")
        with get_conn() as conn:
            _m007_upgrade_admin_role(conn)
            row = conn.execute(
                "SELECT role FROM accounts WHERE username='admin'"
            ).fetchone()
        assert row["role"] == "系統管理員"

    def test_m007_does_not_affect_non_admin_users(self, tmp_db):
        """M007：只升級 username='admin'，其他帳號不受影響。"""
        from repositories.account_repo import create_account
        from core.database import _m007_upgrade_admin_role
        create_account("commander", "1234", "指揮官")
        with get_conn() as conn:
            _m007_upgrade_admin_role(conn)
            row = conn.execute(
                "SELECT role FROM accounts WHERE username='commander'"
            ).fetchone()
        assert row["role"] == "指揮官"


class TestSchemaMigrationsApi:
    def test_list_migrations_requires_admin_pin(self, client):
        """/api/admin/schema-migrations Admin PIN 已設定但無 PIN header → 403。"""
        set_admin_pin("1234", "test")
        r = client.get("/api/admin/schema-migrations")
        assert r.status_code == 403

    def test_list_migrations_returns_all_versions(self, client):
        """正確 PIN → 200，回傳所有已套用的 migrations。"""
        set_admin_pin("1234", "test")
        r = client.get("/api/admin/schema-migrations",
                       headers={"X-Admin-PIN": "1234"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) == len(_MIGRATIONS)
        versions = [m["version"] for m in data]
        assert versions == sorted(versions)  # 依版本號排序

    def test_list_migrations_record_structure(self, client):
        """每筆 migration 紀錄需包含 version / name / applied_at。"""
        set_admin_pin("1234", "test")
        r = client.get("/api/admin/schema-migrations",
                       headers={"X-Admin-PIN": "1234"})
        for m in r.json():
            assert "version"    in m
            assert "name"       in m
            assert "applied_at" in m

    def test_admin_status_includes_schema_version(self, client):
        """/api/admin/status 回傳 schema_version 欄位。"""
        r = client.get("/api/admin/status")
        assert r.status_code == 200
        assert "schema_version" in r.json()
        assert r.json()["schema_version"] == max(v for v, _, _ in _MIGRATIONS)
