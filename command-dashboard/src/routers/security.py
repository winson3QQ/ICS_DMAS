"""
routers/security.py — 安全相關端點（C1-B）

目前只有 CSP violation 收集端點。未來 C1-D 稽核軌跡、C1-A MFA 等可能加入。
"""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response

router = APIRouter(prefix="/api/security", tags=["安全"])

# 獨立 logger，未來 C1-D structlog JSON 上線後改 sink 到 SIEM
_logger = logging.getLogger("ics.security.csp")


@router.post("/csp-report")
async def csp_report(request: Request):
    """
    瀏覽器 CSP violation 自動 POST 至此端點（report-uri 指定）。

    body 格式（W3C CSP Level 2）：
        {"csp-report": {"document-uri": ..., "violated-directive": ..., ...}}

    處理：log 為 WARNING；不存 DB（觀察期量可能大；C1-D 後再考慮持久化）。
    回 204 No Content（CSP spec 要求 2xx 回應）。
    """
    try:
        body = await request.body()
        if body:
            try:
                report = json.loads(body)
                _logger.warning("CSP_VIOLATION %s", json.dumps(report, ensure_ascii=False))
            except json.JSONDecodeError:
                _logger.warning("CSP_VIOLATION_MALFORMED %s", body[:500])
    except Exception as e:
        # 違規回報絕不可影響正常運作，吞掉所有錯誤
        _logger.error("csp_report handler error: %s", e)

    return Response(status_code=204)
