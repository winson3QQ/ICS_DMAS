"""
tests/unit/test_rbac.py — RBAC role gate 測試

unit  ：check_role_level() 純函數矩陣測試、require_role() factory 驗證
security：require_role() FastAPI Depends 整合（mini app + session DB）
"""

import pytest

from auth.rbac import ROLE_HIERARCHY, check_role_level, require_role


# ─────────────────────────────────────────────────────────────────────────────
# ROLE_HIERARCHY 常數
# ─────────────────────────────────────────────────────────────────────────────

class TestRoleHierarchy:
    def test_has_four_roles(self):
        assert len(ROLE_HIERARCHY) == 4

    def test_all_roles_present(self):
        assert set(ROLE_HIERARCHY) == {"系統管理員", "指揮官", "操作員", "觀察員"}

    def test_sysadmin_is_highest(self):
        assert ROLE_HIERARCHY["系統管理員"] == max(ROLE_HIERARCHY.values())

    def test_observer_is_lowest(self):
        assert ROLE_HIERARCHY["觀察員"] == min(ROLE_HIERARCHY.values())

    def test_strict_order(self):
        assert (ROLE_HIERARCHY["系統管理員"]
                > ROLE_HIERARCHY["指揮官"]
                > ROLE_HIERARCHY["操作員"]
                > ROLE_HIERARCHY["觀察員"])


# ─────────────────────────────────────────────────────────────────────────────
# check_role_level() — 純函數矩陣
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckRoleLevel:
    def _sess(self, role: str) -> dict:
        return {"username": "u", "role": role}

    @pytest.mark.parametrize("user_role,gate,expected", [
        # gate = 觀察員：全部通過
        ("系統管理員", "觀察員", True),
        ("指揮官",     "觀察員", True),
        ("操作員",     "觀察員", True),
        ("觀察員",     "觀察員", True),
        # gate = 操作員：觀察員擋下
        ("系統管理員", "操作員", True),
        ("指揮官",     "操作員", True),
        ("操作員",     "操作員", True),
        ("觀察員",     "操作員", False),
        # gate = 指揮官：操作員 + 觀察員擋下
        ("系統管理員", "指揮官", True),
        ("指揮官",     "指揮官", True),
        ("操作員",     "指揮官", False),
        ("觀察員",     "指揮官", False),
        # gate = 系統管理員：只有系統管理員通過
        ("系統管理員", "系統管理員", True),
        ("指揮官",     "系統管理員", False),
        ("操作員",     "系統管理員", False),
        ("觀察員",     "系統管理員", False),
    ])
    def test_matrix(self, user_role, gate, expected):
        assert check_role_level(self._sess(user_role), gate) == expected

    def test_unknown_role_blocked_everywhere(self):
        """未知 role 的 session 視為 level 0，任何 gate 都擋下"""
        for gate in ROLE_HIERARCHY:
            assert check_role_level({"role": "外星人"}, gate) is False

    def test_missing_role_key_blocked(self):
        """session 無 role 欄位 → 視為 level 0"""
        assert check_role_level({}, "觀察員") is False

    def test_multi_gate_takes_lowest(self):
        """require_role("觀察員","指揮官") 取最低等級（觀察員），全部 role 通過"""
        for role in ROLE_HIERARCHY:
            assert check_role_level(self._sess(role), "觀察員", "指揮官") is True


# ─────────────────────────────────────────────────────────────────────────────
# require_role() factory — 驗證邏輯（不需 DB）
# ─────────────────────────────────────────────────────────────────────────────

class TestRequireRoleFactory:
    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="至少需要"):
            require_role()

    def test_unknown_role_raises(self):
        with pytest.raises(ValueError, match="未知 role"):
            require_role("外星人")

    def test_mix_valid_invalid_raises(self):
        with pytest.raises(ValueError, match="未知 role"):
            require_role("操作員", "神仙")

    def test_returns_depends_object(self):
        from fastapi.params import Depends as DependsType
        result = require_role("操作員")
        assert isinstance(result, DependsType)

    def test_all_valid_roles_accepted(self):
        for role in ROLE_HIERARCHY:
            result = require_role(role)
            from fastapi.params import Depends as DependsType
            assert isinstance(result, DependsType)


# ─────────────────────────────────────────────────────────────────────────────
# require_role() FastAPI Depends 整合測試
# ─────────────────────────────────────────────────────────────────────────────

class TestRequireRoleDependency:
    """用 mini FastAPI app 驗證 require_role 的完整 401/403 行為。"""

    @pytest.fixture
    def mini_client(self, tmp_db):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mini = FastAPI()

        @mini.get("/observer-gate")
        def _o(_: dict = require_role("觀察員")):
            return {"ok": True}

        @mini.get("/operator-gate")
        def _op(_: dict = require_role("操作員")):
            return {"ok": True}

        @mini.get("/commander-gate")
        def _c(_: dict = require_role("指揮官")):
            return {"ok": True}

        @mini.get("/sysadmin-gate")
        def _s(_: dict = require_role("系統管理員")):
            return {"ok": True}

        with TestClient(mini, raise_server_exceptions=True) as c:
            yield c

    def _tok(self, role: str) -> str:
        from auth.service import create_session
        return create_session({"username": "u", "role": role, "display_name": None})

    # ── 無 session ─────────────────────────────────────────────────

    def test_no_session_returns_401(self, mini_client):
        assert mini_client.get("/observer-gate").status_code == 401

    def test_invalid_token_returns_401(self, mini_client):
        h = {"X-Session-Token": "not-a-real-token"}
        assert mini_client.get("/operator-gate", headers=h).status_code == 401

    # ── 系統管理員 通過所有 gate ────────────────────────────────────

    def test_sysadmin_passes_all_gates(self, mini_client):
        h = {"X-Session-Token": self._tok("系統管理員")}
        for ep in ["/observer-gate", "/operator-gate", "/commander-gate", "/sysadmin-gate"]:
            assert mini_client.get(ep, headers=h).status_code == 200, ep

    # ── 觀察員 只能過觀察員 gate ─────────────────────────────────

    def test_observer_only_passes_observer_gate(self, mini_client):
        h = {"X-Session-Token": self._tok("觀察員")}
        assert mini_client.get("/observer-gate", headers=h).status_code == 200
        assert mini_client.get("/operator-gate", headers=h).status_code == 403
        assert mini_client.get("/commander-gate", headers=h).status_code == 403
        assert mini_client.get("/sysadmin-gate", headers=h).status_code == 403

    # ── 操作員 可過觀察員 + 操作員 gate ────────────────────────────

    def test_operator_passes_observer_and_operator_gates(self, mini_client):
        h = {"X-Session-Token": self._tok("操作員")}
        assert mini_client.get("/observer-gate", headers=h).status_code == 200
        assert mini_client.get("/operator-gate", headers=h).status_code == 200
        assert mini_client.get("/commander-gate", headers=h).status_code == 403
        assert mini_client.get("/sysadmin-gate", headers=h).status_code == 403

    # ── 指揮官 被 系統管理員 gate 擋下 ──────────────────────────────

    def test_commander_blocked_by_sysadmin_gate(self, mini_client):
        h = {"X-Session-Token": self._tok("指揮官")}
        assert mini_client.get("/observer-gate", headers=h).status_code == 200
        assert mini_client.get("/operator-gate", headers=h).status_code == 200
        assert mini_client.get("/commander-gate", headers=h).status_code == 200
        assert mini_client.get("/sysadmin-gate", headers=h).status_code == 403

    # ── 401 vs 403 區分 ─────────────────────────────────────────

    def test_403_not_401_for_valid_session_wrong_role(self, mini_client):
        """session 有效但 role 不足 → 403，不是 401"""
        h = {"X-Session-Token": self._tok("觀察員")}
        r = mini_client.get("/operator-gate", headers=h)
        assert r.status_code == 403

    def test_401_for_no_token(self, mini_client):
        """完全無 token → 401，不是 403"""
        r = mini_client.get("/operator-gate")
        assert r.status_code == 401
