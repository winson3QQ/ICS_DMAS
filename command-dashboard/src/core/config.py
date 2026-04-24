"""
core/config.py — 環境變數與路徑設定
"""

import os
from pathlib import Path

# ── 路徑 ──────────────────────────────────
SRC_DIR     = Path(__file__).parent.parent
BASE_DIR    = SRC_DIR.parent
DATA_DIR    = BASE_DIR / "data"
STATIC_DIR  = BASE_DIR / "static"
MBTILES_DIR = STATIC_DIR / "tiles"

DB_PATH = DATA_DIR / "ics.db"

# ── Session ───────────────────────────────
SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "28800"))  # 秒，預設 8 小時（一次演練時長）
# 注意：PinLock（UI 層 idle 鎖定）是獨立機制，與此 server-side timeout 無關

# ── App ───────────────────────────────────
APP_VERSION = "2.0.0"   # C0 重構版

# ── 認證豁免路由 ──────────────────────────
# (method, path) 完整匹配
AUTH_EXEMPT_EXACT: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/api/auth/login"),
    ("GET",  "/api/status"),
    ("GET",  "/docs"),
    ("GET",  "/openapi.json"),
    ("GET",  "/"),
})

# path 前綴匹配（任何 method）
AUTH_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/static/",
    "/api/map/tiles/",
)
