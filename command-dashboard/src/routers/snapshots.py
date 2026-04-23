from fastapi import APIRouter, HTTPException
from schemas.snapshot import SnapshotIn
from repositories.snapshot_repo import upsert_snapshot, get_snapshots

router = APIRouter(prefix="/api/snapshots", tags=["快照"])

_TYPE_MAP = {
    "snapshot_shelter": "shelter", "snapshot_medical": "medical",
    "snapshot_forward": "forward", "snapshot_security": "security",
    "snapshot_ccp": "ccp",         "snapshot_evac": "evac",
    "shelter": "shelter",          "medical": "medical",
    "forward": "forward",          "security": "security",
    "ccp": "ccp",                  "evac": "evac",
}


@router.post("")
def post_snapshot(snap: SnapshotIn):
    """各組 Pi 推送快照（idempotent：同 snapshot_id 忽略）"""
    node_type = _TYPE_MAP.get(snap.type)
    if not node_type:
        raise HTTPException(400, f"未知的 type: {snap.type}")
    data = snap.model_dump()
    data["node_type"] = node_type
    return upsert_snapshot(data)


@router.get("/{node_type}")
def get_snap(node_type: str, limit: int = 20):
    return get_snapshots(node_type, limit)
