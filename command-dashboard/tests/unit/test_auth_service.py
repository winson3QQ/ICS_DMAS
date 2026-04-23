"""
unit/test_auth_service.py — auth/service.py session 管理測試

不依賴 DB，直接操作 in-memory _sessions dict。
"""

import pytest
import time

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clean_sessions():
    from auth.service import _sessions
    _sessions.clear()
    yield
    _sessions.clear()


class TestCreateSession:
    def test_returns_uuid_string(self):
        from auth.service import create_session
        token = create_session({"username": "alice", "role": "operator"})
        assert isinstance(token, str)
        assert len(token) == 36  # UUID4 格式

    def test_session_stored(self):
        from auth.service import create_session, _sessions
        token = create_session({"username": "alice", "role": "operator"})
        assert token in _sessions
        assert _sessions[token]["username"] == "alice"

    def test_unique_tokens(self):
        from auth.service import create_session
        t1 = create_session({"username": "u1", "role": "operator"})
        t2 = create_session({"username": "u2", "role": "operator"})
        assert t1 != t2


class TestGetSession:
    def test_valid_token(self):
        from auth.service import create_session, get_session
        token = create_session({"username": "bob", "role": "commander"})
        sess = get_session(token)
        assert sess is not None
        assert sess["username"] == "bob"

    def test_invalid_token(self):
        from auth.service import get_session
        assert get_session("nonexistent-token") is None

    def test_expired_session(self):
        from auth.service import create_session, get_session, _sessions
        token = create_session({"username": "x", "role": "operator"})
        # 直接把 last_active 設到很久以前
        _sessions[token]["last_active"] = time.time() - 9999
        assert get_session(token) is None
        # 過期 session 應被清除
        assert token not in _sessions


class TestDestroySession:
    def test_removes_session(self):
        from auth.service import create_session, destroy_session, _sessions
        token = create_session({"username": "eve", "role": "operator"})
        result = destroy_session(token)
        assert result is not None
        assert token not in _sessions

    def test_nonexistent_returns_none(self):
        from auth.service import destroy_session
        assert destroy_session("ghost-token") is None


class TestSessionRemaining:
    def test_fresh_session_has_remaining(self):
        from auth.service import create_session, session_remaining
        token = create_session({"username": "u", "role": "operator"})
        rem = session_remaining(token)
        assert rem > 0

    def test_nonexistent_returns_zero(self):
        from auth.service import session_remaining
        assert session_remaining("ghost") == 0
