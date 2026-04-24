"""
tests/security/test_admin_gate.py — Admin 權限集中化前的守門測試

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
from repositories.config_repo import set_admin_pin


# ─────────────────────────────────────────────────────────────────
# Session 有效但無 Admin PIN → 仍 403
# ─────────────────────────────────────────────────────────────────

class TestSessionVsAdminPin:
    def test_valid_session_without_admin_pin_returns_403(self, client):
        """有效 session token + 無 X-Admin-PIN → 403（session 無法繞過 admin PIN）"""
        r = client.post("/api/auth/login", json={"username": "admin", "pin": "1234"})
        token = r.json()["session_id"]
        r2 = client.get("/api/admin/accounts", headers={"X-Session-Token": token})
        assert r2.status_code == 403

    def test_valid_session_with_wrong_admin_pin_returns_403(self, client):
        """有效 session + 錯誤 X-Admin-PIN → 403"""
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
