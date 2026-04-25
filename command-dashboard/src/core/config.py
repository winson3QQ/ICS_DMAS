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
APP_VERSION = "2.1.0"   # C1-A Phase 2 Steps 1-5：4-role RBAC core（M006 migration, require_role() gate, 雙重認證, endpoint gates, privilege escalation protection）；30 security tests

# ── CORS（C1-B）──────────────────────────
# 架構備忘：PWA→Pi→Command 為 hub-and-spoke，瀏覽器無跨源呼叫，CORS 在主流程中無作用。
# 保留 middleware 是為未來 TTX Orchestrator（C5-A 獨立服務）與 Tier 3 開放 API（C5-E）預留。
# 部署時由 /etc/ics/command.env 的 ALLOWED_ORIGINS 覆寫；預設只開本機（dev）。
_default_origins = "http://localhost:8000,http://127.0.0.1:8000,https://localhost,https://127.0.0.1"
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()
]

# ── 安全標頭（C1-B）────────────────────────
# CSP_MODE: "report-only"（觀察期）→ "enforce"（正式擋）
# 由 nginx 反代終結 TLS 並注入 HSTS（避免 FastAPI 在 HTTP dev 環境也送 HSTS 鎖死瀏覽器），
# CSP / X-Frame-Options / X-Content-Type-Options 由 FastAPI middleware 負責（與應用語義耦合）。
CSP_MODE: str = os.getenv("CSP_MODE", "report-only")  # "report-only" | "enforce"
CSP_REPORT_URI: str = os.getenv("CSP_REPORT_URI", "/api/security/csp-report")
ENABLE_SECURITY_HEADERS: bool = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"

# ── 認證豁免路由 ──────────────────────────
# (method, path) 完整匹配
AUTH_EXEMPT_EXACT: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/api/auth/login"),
    ("GET",  "/api/status"),
    ("GET",  "/docs"),
    ("GET",  "/openapi.json"),
    ("GET",  "/"),
    # CSP violation report：瀏覽器自動 POST，不帶 session token
    ("POST", "/api/security/csp-report"),
})

# path 前綴匹配（任何 method）
AUTH_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/static/",
    "/api/map/tiles/",
)
