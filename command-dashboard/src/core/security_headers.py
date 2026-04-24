"""
core/security_headers.py — 安全 HTTP 標頭 middleware（C1-B）

分工：
  - HSTS / X-Frame-Options / X-Content-Type-Options / Referrer-Policy：由 nginx 注入
    （見 deploy/nginx/conf.d/security-headers.conf）
  - CSP：由本 middleware 注入（與應用語義耦合）

CSP 階段策略（業界 staged approach）：
  - C1-B 階段：basic CSP + 'unsafe-inline'（妥協現有 inline onclick / style="" 共 600+ 處）
  - C1-F 階段（前端模組化後）：升級為 nonce-based + strict-dynamic（CSP Level 3）

模式切換：環境變數 CSP_MODE=report-only|enforce
  - report-only：送 Content-Security-Policy-Report-Only，違規回報不擋
  - enforce：送 Content-Security-Policy，違規擋下
"""

from fastapi import Request
from fastapi.responses import Response

from core.config import CSP_MODE, CSP_REPORT_URI, ENABLE_SECURITY_HEADERS


def _build_csp() -> str:
    """組 CSP 字串。所有 directive 集中在此，便於 audit。"""
    directives = [
        # 預設來源
        "default-src 'self'",

        # JS：本地 + inline（待 C1-F 移除）
        "script-src 'self' 'unsafe-inline'",

        # CSS：本地 + inline + Google Fonts CSS
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",

        # 字型：本地 + Google Fonts 字型檔
        "font-src 'self' https://fonts.gstatic.com",

        # 圖片：本地 + data:（base64 icon）+ blob:（截圖）
        "img-src 'self' data: blob:",

        # API / WebSocket：本地（含 wss/ws，PWA Pi WS 連線）
        "connect-src 'self' wss: ws:",

        # 物件、frame、worker
        "object-src 'none'",
        "frame-ancestors 'none'",
        "worker-src 'self' blob:",

        # 表單 action 限同源
        "form-action 'self'",

        # base href 限同源（防 base injection）
        "base-uri 'self'",

        # 違規回報
        f"report-uri {CSP_REPORT_URI}",
    ]
    return "; ".join(directives)


CSP_POLICY = _build_csp()
CSP_HEADER_NAME = (
    "Content-Security-Policy-Report-Only"
    if CSP_MODE == "report-only"
    else "Content-Security-Policy"
)


async def security_headers_middleware(request: Request, call_next) -> Response:
    """注入 CSP header；其他安全 header 由 nginx 負責。"""
    response = await call_next(request)
    if ENABLE_SECURITY_HEADERS:
        response.headers[CSP_HEADER_NAME] = CSP_POLICY
    return response
