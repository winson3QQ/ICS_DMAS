
from fastapi import APIRouter

from auth.rbac import require_role
from core.config import APP_VERSION, DB_PATH
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
def audit_log_endpoint(limit: int = 100, _: dict = require_role("觀察員")):
    return get_audit_log(limit)


@router.get("/api/health", tags=["系統"])
def health():
    return {"status": "ok", "version": APP_VERSION, "db": str(DB_PATH)}


@router.get("/api/status", tags=["系統"])
def status():
    return {"status": "ok", "version": APP_VERSION}
