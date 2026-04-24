"""
tests/conftest.py — 共用 fixtures

DB 隔離策略：
  每個測試使用 tmp_path 建立獨立 SQLite 檔案，
  並 monkeypatch core.database.DB_PATH，確保測試之間不互汙染。

Session 隔離：
  sessions 存在 SQLite（sessions 表），隨 tmp_db 的獨立 DB 自動隔離。
  _clear_sessions autouse fixture 在測試前後刪除 sessions 表資料，
  防止跨測試 session 洩漏（包含無 tmp_db 的測試情境）。
"""

import sys
from pathlib import Path

# 讓測試能 import src/ 下的模組
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest


# ── Session 隔離（autouse，所有測試自動套用）────────────────────────────────

def _delete_all_sessions():
    """刪除當前 DB 的所有 sessions（test DB 或 real DB 均適用）"""
    try:
        from core.database import get_conn
        conn = get_conn()
        conn.execute("DELETE FROM sessions")
        conn.commit()
        conn.close()
    except Exception:
        pass  # sessions 表不存在（init_db 尚未執行）時忽略


@pytest.fixture(autouse=True)
def _clear_sessions():
    _delete_all_sessions()
    yield
    _delete_all_sessions()


# ── DB 隔離 ────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """
    每個測試建立獨立 SQLite DB，並在結束後自動刪除。
    monkeypatch 確保所有 get_conn() 呼叫都指向測試 DB。
    """
    db_file = tmp_path / "test_ics.db"
    import core.database
    import core.config
    monkeypatch.setattr(core.config, "DB_PATH", db_file)
    monkeypatch.setattr(core.database, "DB_PATH", db_file)
    from core.database import init_db
    init_db()
    return db_file


# ── FastAPI TestClient ────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_db):
    """
    FastAPI TestClient，綁定測試 DB。
    startup event 會自動執行 init_db + ensure_default_admin。
    """
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def session_token(client):
    """已登入的 session_id（預設 admin/1234）"""
    r = client.post("/api/auth/login", json={"username": "admin", "pin": "1234"})
    assert r.status_code == 200, f"登入失敗：{r.text}"
    return r.json()["session_id"]


@pytest.fixture
def auth(session_token):
    """帶認證的 header dict，直接傳給 client.get(..., headers=auth)"""
    return {"X-Session-Token": session_token}


@pytest.fixture
def active_exercise(client, auth):
    """建立並啟動一個 TTX 演練，回傳 exercise dict"""
    r = client.post("/api/exercises",
                    json={"name": "fixture-exercise", "type": "ttx"},
                    headers=auth)
    assert r.status_code == 200
    ex = r.json()
    r2 = client.post(f"/api/exercises/{ex['id']}/activate",
                     json={}, headers=auth)
    assert r2.status_code == 200
    return r2.json()
