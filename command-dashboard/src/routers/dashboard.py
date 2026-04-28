
from fastapi import APIRouter

from core.config import APP_VERSION, CMD_VERSION, DB_PATH
from repositories.audit_repo import get_audit_log
from repositories.snapshot_repo import get_latest_snapshot
from services.dashboard_service import build_dashboard

router = APIRouter(tags=["儀表板"])


@router.get("/api/dashboard")
def get_dashboard(exercise_id: int | None = None):
    """前端每 10 秒 polling 的主要端點"""
    return build_dashboard(exercise_id)


@router.get("/api/staff", tags=["人員"])
def get_staff():
    result = {}
    for node_type in ("shelter", "medical", "forward", "security"):
        snap = get_latest_snapshot(node_type)
        if snap:
            extra = snap.get("extra") or {}
            result[node_type] = {
                "staff":         extra.get("staff_list", []),
                "staff_on_duty": snap.get("staff_on_duty"),
                "snapshot_time": snap.get("snapshot_time"),
            }
        else:
            result[node_type] = {"staff": [], "staff_on_duty": None, "snapshot_time": None}
    return result


@router.get("/api/audit_log", tags=["系統"])
def audit_log_endpoint(limit: int = 100):
    return get_audit_log(limit)


@router.get("/api/version", tags=["系統"])
def version():
    """
    前端啟動時 fetch 取版本號（C1-F Q1）。
    - cmd_version：前端 UI 功能版本（Wave 里程碑）
    - server_version：後端 API SemVer
    無需認證（版號非敏感資訊）。
    """
    return {
        "cmd_version":    CMD_VERSION,
        "server_version": APP_VERSION,
    }


@router.get("/api/health", tags=["系統"])
def health():
    return {"status": "ok", "version": APP_VERSION, "db": str(DB_PATH)}


@router.get("/api/status", tags=["系統"])
def status():
    return {"status": "ok", "version": APP_VERSION}
