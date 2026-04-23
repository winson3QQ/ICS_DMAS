from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from repositories.sync_repo import (
    execute_three_pass, get_sync_log, get_sync_conflicts, resolve_conflict
)
from schemas.sync import SyncPushIn, ConflictResolveIn

router = APIRouter(prefix="/api/sync", tags=["三 Pass 同步"])


@router.post("/push")
def sync_push(body: SyncPushIn, request: Request):
    operator = request.headers.get("X-Operator", "auto")
    return execute_three_pass(body.source_unit, body.model_dump(), operator)


@router.get("/log")
def sync_log(source_unit: Optional[str] = None, limit: int = 20):
    return get_sync_log(source_unit, limit)


@router.get("/{sync_id}")
def sync_entry(sync_id: str):
    entry = get_sync_conflicts(sync_id)
    if not entry:
        raise HTTPException(404, "sync_id not found")
    return entry


@router.post("/{sync_id}/resolve")
def resolve(sync_id: str, body: ConflictResolveIn):
    try:
        return resolve_conflict(sync_id, body.conflict_idx, body.action, body.operator)
    except ValueError as e:
        raise HTTPException(404, str(e))
