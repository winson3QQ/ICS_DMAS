"""
tests/security/test_admin_gate.py — Admin 權限集中化前的守門測試 + C2-D Admin PIN 鎖定

核心設計：/api/admin/* 使用兩層獨立認證：
  1. Session auth（middleware 層）：/api/admin/* 豁免 session check
  2. X-Admin-PIN（router 層）：_check_admin_pin() 驗證獨立 admin PIN

守門目標：
  - 有效 session 不等於可存取 admin API（仍需 X-Admin-PIN）
  - 角色（指揮官/操作員）不影響 admin API 存取（PIN 才是關鍵）
  - 角色升級嘗試（operator 改自己 role）→ 403（無 PIN）
  - admin PIN 正確才可操作，與 session role 無關
"""

import pytest
from repositories.config_repo import (
    ADMIN_LOCKOUT_THRESHOLD,
    get_admin_pin_lock_status,
    reset_admin_pin_failures,
    set_admin_pin,
)


# ─────────────────────────────────────────────────────────────────
# Session 有效但無 Admin PIN → 仍 403
# ─────────────────────────────────────────────────────────────────

class TestSessionVsAdminPin:
    def test_valid_session_without_admin_pin_returns_403(self, client):
        """有效 session token + 無 X-Admin-PIN → 403（session 無法繞過 admin PIN）"""
        set_admin_pin("1234", "test")
        r = client.post("/api/auth/login", json={"username": "admin", "pin": "1234"})
        token = r.json()["session_id"]
        r2 = client.get("/api/admin/accounts", headers={"X-Session-Token": token})
        assert r2.status_code == 403

    def test_valid_session_with_wrong_admin_pin_returns_403(self, client):
        """有效 session + 錯誤 X-Admin-PIN → 403"""
        set_admin_pin("1234", "test")
        r = client.post("/api/auth/login", json={"username": "admin", "pin": "1234"})
        token = r.json()["session_id"]
        r2 = client.get("/api/admin/accounts", headers={
            "X-Session-Token": token,
            "X-Admin-PIN": "000000"
        })
        assert r2.status_code == 403

    def test_no_session_with_correct_admin_pin_passes(self, client):
        """無 session + 正確 X-Admin-PIN → 200（admin 端點豁免 session auth）"""
        set_admin_pin("1234", "test")
        r = client.get("/api/admin/accounts", headers={"X-Admin-PIN": "1234"})
        assert r.status_code == 200

    def test_valid_session_with_correct_admin_pin_passes(self, client):
        """有效 session + 正確 X-Admin-PIN → 200"""
        set_admin_pin("1234", "test")
        r = client.post("/api/auth/login", json={"username": "admin", "pin": "1234"})
        token = r.json()["session_id"]
        r2 = client.get("/api/admin/accounts", headers={
            "X-Session-Token": token,
            "X-Admin-PIN": "1234"
        })
        assert r2.status_code == 200


# ─────────────────────────────────────────────────────────────────
# 角色不影響 Admin PIN 驗證
# ─────────────────────────────────────────────────────────────────

class TestRoleVsAdminPin:
    def _create_operator(self, client):
        """建立一個操作員帳號，回傳 (username, session_token)"""
        set_admin_pin("1234", "test")
        client.post("/api/admin/accounts", headers={"X-Admin-PIN": "1234"}, json={
            "username": "op_user", "pin": "5678",
            "role": "操作員", "display_name": "操作員甲", "role_detail": ""
        })
        r = client.post("/api/auth/login", json={"username": "op_user", "pin": "5678"})
        return "op_user", r.json()["session_id"]

    def test_operator_without_admin_pin_gets_403(self, client):
        """操作員角色 + 有效 session + 無 PIN → 403（角色不替代 PIN）"""
        _, token = self._create_operator(client)
        r = client.get("/api/admin/accounts", headers={"X-Session-Token": token})
        assert r.status_code == 403

    def test_operator_with_correct_admin_pin_can_access(self, client):
        """操作員角色 + 正確 X-Admin-PIN → 200（PIN 才是守門關鍵，非角色）"""
        _, token = self._create_operator(client)
        r = client.get("/api/admin/accounts", headers={
            "X-Session-Token": token,
            "X-Admin-PIN": "1234"
        })
        assert r.status_code == 200

    def test_operator_cannot_escalate_own_role_without_pin(self, client):
        """操作員嘗試升級自己的角色（無 PIN）→ 403（角色升級需 admin PIN）"""
        username, token = self._create_operator(client)
        r = client.put(f"/api/admin/accounts/{username}/role", headers={
            "X-Session-Token": token,
        }, json={"role": "指揮官", "role_detail": ""})
        assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────
# Admin PIN 異常邊界
# ─────────────────────────────────────────────────────────────────

class TestAdminPinBoundary:
    def test_admin_pin_not_setup_verify_returns_false(self, tmp_db):
        """admin_pin 未設定（空 DB）→ verify_admin_pin() 直接回傳 False"""
        # 直接測 config_repo 邏輯，不走 API（API 用的是 client fixture 的 DB）
        from repositories.config_repo import verify_admin_pin
        assert verify_admin_pin("1234") is False

    def test_admin_pin_change_takes_effect_immediately(self, client):
        """改 admin PIN 後舊 PIN 立刻失效，新 PIN 立刻生效"""
        set_admin_pin("oldpin", "test")
        # 舊 PIN 有效
        assert client.get("/api/admin/accounts",
                          headers={"X-Admin-PIN": "oldpin"}).status_code == 200
        # 直接用 repo 改 PIN（繞過 API 避免 endpoint 路徑不確定性）
        set_admin_pin("newpin", "test")
        # 舊 PIN 失效
        assert client.get("/api/admin/accounts",
                          headers={"X-Admin-PIN": "oldpin"}).status_code == 403
        # 新 PIN 有效
        assert client.get("/api/admin/accounts",
                          headers={"X-Admin-PIN": "newpin"}).status_code == 200

    def test_delete_nonexistent_account_returns_404(self, client):
        """刪除不存在的帳號（正確 PIN）→ 404"""
        set_admin_pin("1234", "test")
        r = client.delete("/api/admin/accounts/ghost_user",
                          headers={"X-Admin-PIN": "1234"})
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────
# C2-D：Admin PIN 鎖定機制
# ─────────────────────────────────────────────────────────────────

class TestAdminPinLockout:
    """Admin PIN 連續失敗鎖定（C2-D）"""

    def _wrong(self, client, n: int = 1):
        """送出 n 次錯誤 Admin PIN，回傳最後一次 response。"""
        r = None
        for _ in range(n):
            r = client.get("/api/admin/accounts",
                           headers={"X-Admin-PIN": "000000"})
        return r

    def test_single_wrong_pin_returns_403_with_remaining(self, client):
        """單次錯誤 → 403，detail 含剩餘次數。"""
        set_admin_pin("1234", "test")
        r = self._wrong(client, 1)
        assert r.status_code == 403
        assert "剩餘" in r.json()["detail"]

    def test_remaining_count_decrements(self, client):
        """每次失敗剩餘次數遞減。"""
        set_admin_pin("1234", "test")
        r1 = self._wrong(client, 1)
        r2 = self._wrong(client, 1)
        # 兩次結果都是 403，且 r2 的 detail 剩餘次數比 r1 少 1
        assert r1.status_code == r2.status_code == 403
        import re
        n1 = int(re.search(r"剩餘\s*(\d+)", r1.json()["detail"]).group(1))
        n2 = int(re.search(r"剩餘\s*(\d+)", r2.json()["detail"]).group(1))
        assert n2 == n1 - 1

    def test_threshold_wrong_pins_triggers_423(self, client):
        """連續失敗達門檻 → 423 鎖定。"""
        set_admin_pin("1234", "test")
        r = self._wrong(client, ADMIN_LOCKOUT_THRESHOLD)
        assert r.status_code == 423

    def test_locked_correct_pin_still_returns_423(self, client):
        """鎖定中送正確 PIN → 仍然 423（不因 PIN 正確而解鎖）。"""
        set_admin_pin("1234", "test")
        self._wrong(client, ADMIN_LOCKOUT_THRESHOLD)  # 觸發鎖定
        r = client.get("/api/admin/accounts",
                       headers={"X-Admin-PIN": "1234"})
        assert r.status_code == 423

    def test_correct_pin_resets_failure_count(self, client):
        """錯誤 N-1 次後送正確 PIN → 成功且計數清零。"""
        set_admin_pin("1234", "test")
        self._wrong(client, ADMIN_LOCKOUT_THRESHOLD - 1)  # 未鎖定
        r = client.get("/api/admin/accounts",
                       headers={"X-Admin-PIN": "1234"})
        assert r.status_code == 200
        # 成功後計數歸零，再錯一次仍是 403（非 423）
        r2 = self._wrong(client, 1)
        assert r2.status_code == 403
        status = get_admin_pin_lock_status()
        assert status["failed_count"] == 1
        assert not status["locked"]

    def test_lock_status_repo_reflects_lockout(self, client):
        """鎖定後 get_admin_pin_lock_status() 回傳正確狀態。"""
        set_admin_pin("1234", "test")
        self._wrong(client, ADMIN_LOCKOUT_THRESHOLD)
        status = get_admin_pin_lock_status()
        assert status["locked"] is True
        assert status["locked_until"] is not None
        assert status["failed_count"] >= ADMIN_LOCKOUT_THRESHOLD

    def test_reset_admin_pin_failures_clears_lockout(self, client):
        """reset_admin_pin_failures() 可手動清除鎖定（用於測試/緊急解鎖）。"""
        set_admin_pin("1234", "test")
        self._wrong(client, ADMIN_LOCKOUT_THRESHOLD)
        assert get_admin_pin_lock_status()["locked"] is True
        reset_admin_pin_failures()
        assert get_admin_pin_lock_status()["locked"] is False
        # 解鎖後正確 PIN 可以通過
        r = client.get("/api/admin/accounts",
                       headers={"X-Admin-PIN": "1234"})
        assert r.status_code == 200
