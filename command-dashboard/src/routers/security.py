"""
routers/security.py — 安全相關端點（C1-B + C1-F）

端點：
  POST /api/security/csp-report
    - 瀏覽器 CSP violation 自動 POST（report-uri 指定）
    - 接受 application/csp-report 與 application/json 兩種 Content-Type
    - 寫入 csp_violations 表（C1-F RV2-01）
    - rate limit：60 次/分鐘/source_ip（防 violation flood）
    - 無需認證（已在 config.AUTH_EXEMPT_EXACT 與 first_run_gate 白名單）
"""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response

from core.database import get_conn
from core.rate_limit import FixedWindowLimiter

router = APIRouter(prefix="/api/security", tags=["安全"])

# 獨立 logger，未來 C1-D structlog JSON 上線後改 sink 到 SIEM
_logger = logging.getLogger("ics.security.csp")

# Rate limiter：60 次/分鐘/IP，防 violation flood
# on_throttle callback 預留給 C1-D audit log 接入（目前只 log WARNING）
def _on_csp_throttle(source_ip: str, count: int) -> None:
    _logger.warning("CSP_REPORT_RATE_LIMIT_HIT ip=%s count=%d", source_ip, count)

_csp_limiter = FixedWindowLimiter(
    limit=60,
    window_sec=60,
    on_throttle=_on_csp_throttle,
)


@router.post("/csp-report")
async def csp_report(request: Request):
    """
    瀏覽器 CSP violation 自動 POST 至此端點（report-uri 指定）。

    body 格式（W3C CSP Level 2）：
        {"csp-report": {"document-uri": ..., "violated-directive": ..., ...}}

    處理：
      1. rate limit 60/min/IP（超限回 429，不寫 DB）
      2. 解析 body（容錯：malformed 仍回 204）
      3. 寫入 csp_violations 表（持久化，供 deployment monitoring 查詢）
      4. 回 204 No Content（CSP spec 要求 2xx 回應）
    """
    source_ip = (request.client.host if request.client else None) or "unknown"

    # Rate limit 檢查
    if not _csp_limiter.check(source_ip):
        return Response(status_code=429)

    violated_directive = None
    blocked_uri        = None
    document_uri       = None
    raw_report         = None

    try:
        body = await request.body()
        if body:
            try:
                report = json.loads(body)
                raw_report = json.dumps(report, ensure_ascii=False)
                # W3C CSP Level 2 格式：{"csp-report": {...}}
                inner = report.get("csp-report") or report
                violated_directive = inner.get("violated-directive") or inner.get("effectiveDirective")
                blocked_uri        = inner.get("blocked-uri")
                document_uri       = inner.get("document-uri")
                _logger.warning(
                    "CSP_VIOLATION directive=%s blocked=%s doc=%s ip=%s",
                    violated_directive, blocked_uri, document_uri, source_ip,
                )
            except json.JSONDecodeError:
                raw_report = body[:2000].decode("utf-8", errors="replace")
                _logger.warning("CSP_VIOLATION_MALFORMED ip=%s body=%s", source_ip, raw_report[:200])
    except Exception as e:
        # 違規回報絕不可影響正常運作，吞掉所有錯誤
        _logger.error("csp_report handler error: %s", e)
        return Response(status_code=204)

    # 寫入 DB（非同步阻塞但 SQLite 寫入極快，可接受）
    try:
        conn = get_conn()
        try:
            conn.execute(
                """INSERT INTO csp_violations
                   (source_ip, violated_directive, blocked_uri, document_uri, raw_report)
                   VALUES (?, ?, ?, ?, ?)""",
                (source_ip, violated_directive, blocked_uri, document_uri, raw_report),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        _logger.error("csp_violations DB write error: %s", e)

    return Response(status_code=204)
