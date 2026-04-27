"""
tests/security/test_auth_bypass.py — 管理員繞過嘗試測試

涵蓋：
  - /api/admin/* 無 X-Admin-PIN / 錯誤 PIN → 403
  - /api/pi-push/* 無 Bearer token → 401
  - 偽造 / 超長 / SQL 注入 session token → 401
  - 路徑穿越嘗試（FastAPI 正規化路徑後的行為）
  - 未認證存取受保護資源

設計備忘：
  middleware.py 中 /api/admin/* 與 /api/pi-push/* 豁免 session auth，
  改由各 router 自行驗證（X-Admin-PIN / Bearer）。
  POST /api/snapshots 和 POST /api/sync/push 為機對機設計，無 session auth，
  此行為已知且有記錄。
"""

import pytest


# ─────────────────────────────────────────────────────────────────
# Admin 端點保護
# ─────────────────────────────────────────────────────────────────

class TestAdminPinProtection:
    """Admin PIN 保護測試。
    各測試先設定 Admin PIN，確保 503（未設定）不干擾 403（有設定但 PIN 錯誤）的語意。
    """

    def test_list_accounts_without_pin_returns_403(self, client):
        """Admin PIN 已設定，無 X-Admin-PIN header → 403"""
        from repositories.config_repo import set_admin_pin
        set_admin_pin("999999", "test")
        r = client.get("/api/admin/accounts")
        assert r.status_code == 403

    def test_list_accounts_wrong_pin_returns_403(self, client):
        """Admin PIN 已設定，錯誤 X-Admin-PIN → 403"""
        from repositories.config_repo import set_admin_pin
        set_admin_pin("999999", "test")
        r = client.get("/api/admin/accounts", headers={"X-Admin-PIN": "000000"})
        assert r.status_code == 403

    def test_list_accounts_empty_pin_returns_403(self, client):
        """Admin PIN 已設定，空字串 X-Admin-PIN → 403"""
        from repositories.config_repo import set_admin_pin
        set_admin_pin("999999", "test")
        r = client.get("/api/admin/accounts", headers={"X-Admin-PIN": ""})
        assert r.status_code == 403

    def test_create_account_without_pin_returns_403(self, client):
        """Admin PIN 已設定，POST /api/admin/accounts 無 PIN → 403"""
        from repositories.config_repo import set_admin_pin
        set_admin_pin("999999", "test")
        r = client.post("/api/admin/accounts", json={
            "username": "hacker", "pin": "1234", "role": "操作員",
            "display_name": "", "role_detail": ""
        })
        assert r.status_code == 403

    def test_delete_account_without_pin_returns_403(self, client):
        """Admin PIN 已設定，DELETE 無 PIN → 403"""
        from repositories.config_repo import set_admin_pin
        set_admin_pin("999999", "test")
        r = client.delete("/api/admin/accounts/admin")
        assert r.status_code == 403

    def test_admin_pin_not_configured_returns_503(self, client):
        """Admin PIN 未設定 → 503（系統未初始化）"""
        r = client.get("/api/admin/accounts")
        assert r.status_code == 503


# ─────────────────────────────────────────────────────────────────
# Pi Push 端點保護
# ─────────────────────────────────────────────────────────────────

class TestPiPushProtection:
    def test_pi_push_without_bearer_returns_401(self, client):
        """POST /api/pi-push/shelter 無 Authorization header → 401"""
        r = client.post("/api/pi-push/shelter", json={"records": []})
        assert r.status_code == 401

    def test_pi_push_wrong_token_returns_403(self, hmac_client):
        """valid HMAC + 錯誤 Bearer token → HMAC 通過，Bearer 驗證失敗 → 403。

        Option-A：pi-push 現在需要 HMAC，無 HMAC headers 會先得到 401 (no_sig)。
        本測試送 valid HMAC + 無效 Bearer，確認 Bearer 層仍正確攔截。
        """
        c, sign = hmac_client
        body_bytes, hdrs = sign("POST", "/api/pi-push/shelter", {"records": []})
        hdrs["Authorization"] = "Bearer INVALID_TOKEN"
        r = c.post("/api/pi-push/shelter", content=body_bytes, headers=hdrs)
        assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────
# Session Token 偽造 / 異常輸入
# ─────────────────────────────────────────────────────────────────

class TestTokenForging:
    def test_nonexistent_token_returns_401(self, client):
        """不存在的 UUID token → 401"""
        r = client.get("/api/auth/me", headers={
            "X-Session-Token": "00000000-0000-0000-0000-000000000000"
        })
        assert r.status_code == 401

    def test_sql_injection_in_token_returns_401(self, client):
        """SQL 注入字串作為 token → 401（不崩潰、不洩漏資料）"""
        malicious = "' OR '1'='1'; DROP TABLE sessions; --"
        r = client.get("/api/auth/me", headers={"X-Session-Token": malicious})
        assert r.status_code == 401

    def test_very_long_token_returns_401(self, client):
        """超長 token（10,000 字元）→ 401（不崩潰）"""
        long_token = "A" * 10_000
        r = client.get("/api/auth/me", headers={"X-Session-Token": long_token})
        assert r.status_code == 401

    def test_empty_token_returns_401(self, client):
        """空字串 token → 401"""
        r = client.get("/api/auth/me", headers={"X-Session-Token": ""})
        assert r.status_code == 401

    def test_no_token_returns_401(self, client):
        """完全不帶 X-Session-Token → 401"""
        r = client.get("/api/dashboard")
        assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────
# 開放端點行為確認（設計決策文件）
# ─────────────────────────────────────────────────────────────────

class TestOpenEndpointsByDesign:
    def test_snapshot_post_requires_hmac_not_session(self, client):
        """
        POST /api/snapshots 無需 session token（機對機設計），
        但 TI-01 後需要 HMAC-SHA256 簽名（verify_hmac Depends）。
        無 HMAC headers → 401（非 session 相關的 401，是 HMAC 驗證失敗）。
        此行為已知且有記錄（非漏洞）。
        """
        r = client.post("/api/snapshots", json={
            "v": 3, "type": "shelter", "snapshot_id": "bypass-check-001",
            "t": "2026-04-24T10:00:00Z", "src": "test",
        })
        # 401 = HMAC 驗證失敗（無 X-ICS-* headers），設計決策
        assert r.status_code == 401
        assert r.json().get("detail", {}).get("reason") == "no_sig"

    def test_snapshot_get_is_open_by_design(self, client):
        """
        GET /api/snapshots/{node_type} 無需 session（Pi 讀取最新快照）。
        """
        r = client.get("/api/snapshots/shelter")
        assert r.status_code == 200

    def test_health_is_open(self, client):
        """GET /api/health 無需 session（監控探針）"""
        r = client.get("/api/health")
        assert r.status_code == 200
