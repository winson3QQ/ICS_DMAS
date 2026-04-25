"""
integration/test_account_repo.py — 帳號 CRUD 與認證流程

直接操作 SQLite（透過 tmp_db fixture），不起 HTTP server。
"""

import pytest

pytestmark = pytest.mark.integration


class TestCreateAccount:
    def test_create_and_retrieve(self, tmp_db):
        from repositories.account_repo import create_account, get_all_accounts
        acc = create_account("alice", "5678", "操作員", "前進組", "operator")
        assert acc["username"] == "alice"
        accounts = get_all_accounts()
        found = next((a for a in accounts if a["username"] == "alice"), None)
        assert found is not None
        assert found["role"] == "操作員"

    def test_duplicate_username_raises(self, tmp_db):
        from repositories.account_repo import create_account
        import sqlite3
        create_account("bob", "1234", "操作員", "", "operator")
        with pytest.raises((sqlite3.IntegrityError, Exception)):
            create_account("bob", "9999", "操作員", "", "operator")

    def test_pin_not_stored_in_plaintext(self, tmp_db):
        from repositories.account_repo import create_account
        import sqlite3
        create_account("carol", "mypin", "操作員", "", "operator")
        conn = sqlite3.connect(str(tmp_db))
        row = conn.execute("SELECT pin_hash FROM accounts WHERE username='carol'").fetchone()
        conn.close()
        assert row[0] != "mypin"


class TestVerifyLogin:
    def test_correct_credentials(self, tmp_db):
        from repositories.account_repo import create_account, verify_login
        create_account("dave", "correct", "操作員", "", "operator")
        acc, reason = verify_login("dave", "correct")
        assert acc is not None and reason == "ok"
        assert acc["username"] == "dave"

    def test_wrong_pin(self, tmp_db):
        from repositories.account_repo import create_account, verify_login
        create_account("eve", "right", "操作員", "", "operator")
        acc, reason = verify_login("eve", "wrong")
        assert acc is None and reason == "bad_pin"

    def test_nonexistent_user(self, tmp_db):
        from repositories.account_repo import verify_login
        acc, reason = verify_login("ghost", "1234")
        assert acc is None and reason == "no_user"

    def test_pin_not_in_response(self, tmp_db):
        from repositories.account_repo import create_account, verify_login
        create_account("frank", "secret", "操作員", "", "operator")
        acc, reason = verify_login("frank", "secret")
        assert reason == "ok"
        assert "pin_hash" not in acc
        assert "pin_salt" not in acc


class TestEnsureDefaultAdmin:
    def test_creates_admin_if_empty(self, tmp_db):
        from repositories.account_repo import ensure_default_admin, get_all_accounts
        ensure_default_admin()
        accounts = get_all_accounts()
        admin = next((a for a in accounts if a["username"] == "admin"), None)
        assert admin is not None
        assert admin["role"] == "指揮官"

    def test_idempotent(self, tmp_db):
        from repositories.account_repo import ensure_default_admin, get_all_accounts
        ensure_default_admin()
        ensure_default_admin()
        accounts = get_all_accounts()
        admin_rows = [a for a in accounts if a["username"] == "admin"]
        assert len(admin_rows) == 1

    def test_default_pin_works(self, tmp_db):
        from repositories.account_repo import ensure_default_admin, verify_login
        ensure_default_admin()
        acc, reason = verify_login("admin", "1234")
        assert acc is not None and reason == "ok"


class TestUpdateAccountStatus:
    def test_suspend_and_login_fails(self, tmp_db):
        from repositories.account_repo import (
            create_account, verify_login, update_account_status
        )
        create_account("target", "1234", "操作員", "", "operator")
        update_account_status("target", "suspended", operator="admin")
        acc, reason = verify_login("target", "1234")
        assert acc is None and reason == "suspended"


class TestSoftDelete:
    def test_soft_delete_hides_account(self, tmp_db):
        """軟刪後帳號不出現在 get_all_accounts()。"""
        from repositories.account_repo import create_account, delete_account, get_all_accounts
        create_account("target", "1234", "操作員")
        delete_account("target", "admin")
        accounts = get_all_accounts()
        assert all(a["username"] != "target" for a in accounts)

    def test_soft_delete_blocks_login(self, tmp_db):
        """軟刪後帳號無法登入（回傳 no_user）。"""
        from repositories.account_repo import create_account, delete_account, verify_login
        create_account("ghost", "1234", "操作員")
        delete_account("ghost", "admin")
        acc, reason = verify_login("ghost", "1234")
        assert acc is None
        assert reason == "no_user"

    def test_soft_delete_invalidates_sessions(self, tmp_db):
        """軟刪後帳號的所有 session 被清除。"""
        from repositories.account_repo import create_account, delete_account
        from auth.service import create_session
        from core.database import get_conn
        create_account("session_user", "1234", "操作員")
        acct = {"username": "session_user", "role": "操作員", "display_name": None}
        create_session(acct)
        # 確認 session 存在
        with get_conn() as conn:
            cnt_before = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE username='session_user'"
            ).fetchone()[0]
        assert cnt_before == 1
        delete_account("session_user", "admin")
        with get_conn() as conn:
            cnt_after = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE username='session_user'"
            ).fetchone()[0]
        assert cnt_after == 0

    def test_soft_delete_twice_returns_false(self, tmp_db):
        """對已軟刪帳號再次軟刪回傳 False。"""
        from repositories.account_repo import create_account, delete_account
        create_account("once", "1234", "操作員")
        assert delete_account("once", "admin") is True
        assert delete_account("once", "admin") is False

    def test_get_all_accounts_include_deleted(self, tmp_db):
        """include_deleted=True 時可看到軟刪帳號。"""
        from repositories.account_repo import create_account, delete_account, get_all_accounts
        create_account("alive", "1234", "操作員")
        create_account("dead", "5678", "操作員")
        delete_account("dead", "admin")
        all_accounts = get_all_accounts(include_deleted=True)
        usernames = [a["username"] for a in all_accounts]
        assert "alive" in usernames
        assert "dead" in usernames

    def test_update_operations_reject_deleted_accounts(self, tmp_db):
        """軟刪後的帳號，update_account_status/pin/role 均回傳 False。"""
        from repositories.account_repo import (
            create_account, delete_account,
            update_account_status, update_account_pin, update_account_role,
        )
        create_account("zombie", "1234", "操作員")
        delete_account("zombie", "admin")
        assert update_account_status("zombie", "active", "admin") is False
        assert update_account_pin("zombie", "9999", "admin") is False
        assert update_account_role("zombie", "指揮官", "admin") is False


class TestValidRoles:
    def test_valid_roles_contains_four_roles(self, tmp_db):
        """VALID_ROLES 包含全部 4 個 role。"""
        from repositories.account_repo import VALID_ROLES
        assert VALID_ROLES == {"系統管理員", "指揮官", "操作員", "觀察員"}

    def test_ensure_initial_admin_token_creates_sysadmin(self, tmp_db):
        """ensure_initial_admin_token() 建立 系統管理員 role。"""
        import tempfile
        from repositories.account_repo import ensure_initial_admin_token, get_all_accounts
        with tempfile.TemporaryDirectory() as d:
            ensure_initial_admin_token(token_dir=d)
        admins = [a for a in get_all_accounts() if a["username"] == "admin"]
        assert len(admins) == 1
        assert admins[0]["role"] == "系統管理員"

    def test_is_first_run_required_works_for_sysadmin(self, tmp_db):
        """is_first_run_required() 對 系統管理員 is_default_pin=1 正確觸發。"""
        import tempfile
        from repositories.account_repo import ensure_initial_admin_token, is_first_run_required
        with tempfile.TemporaryDirectory() as d:
            ensure_initial_admin_token(token_dir=d)
        assert is_first_run_required() is True


class TestLoginLockoutReset:
    def test_successful_login_resets_failed_count(self, tmp_db):
        """連續 3 次錯誤 PIN 後，正確登入 → failed_login_count 歸零、locked_until 清除"""
        from repositories.account_repo import create_account, verify_login
        from core.database import get_conn

        create_account("reset_user", "correct", "操作員", "", "operator")

        # 累積 3 次錯誤
        for _ in range(3):
            acc, reason = verify_login("reset_user", "wrong")
            assert acc is None
            assert reason == "bad_pin"

        # 正確登入
        acc, reason = verify_login("reset_user", "correct")
        assert acc is not None
        assert reason == "ok"

        # DB 確認歸零
        conn = get_conn()
        row = conn.execute(
            "SELECT failed_login_count, locked_until FROM accounts WHERE username=?",
            ("reset_user",),
        ).fetchone()
        conn.close()

        assert row["failed_login_count"] == 0
        assert row["locked_until"] is None
