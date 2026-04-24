from fastapi import APIRouter, HTTPException, Request

from auth.service import validate_session
from repositories.config_repo import get_config, set_config
from schemas.admin import ConfigIn

router = APIRouter(prefix="/api/config", tags=["系統設定"])


@router.get("/{key}")
def read_config(key: str, request: Request):
    validate_session(request)
    if key == "admin_pin":
        raise HTTPException(403, "不可讀取 admin_pin")
    return {"key": key, "value": get_config(key)}


@router.post("/{key}")
def write_config(key: str, body: ConfigIn, request: Request):
    sess = validate_session(request)
    if sess["role"] != "指揮官":
        raise HTTPException(403, "僅指揮官可修改設定")
    if key == "admin_pin":
        raise HTTPException(403, "請使用 /api/admin/pin 變更管理員 PIN")
    set_config(key, body.value, sess["username"])
    return {"ok": True}
