from pydantic import BaseModel
from typing import Optional


class SnapshotIn(BaseModel):
    """通用快照格式。相容 QR-SHELTER / QR-MEDICAL / QR-FORWARD / QR-SECURITY。"""
    v:           int
    type:        str
    snapshot_id: str
    t:           str              # ISO 8601 UTC
    src:         str

    source: Optional[str] = "auto"  # auto / qr_scan / auto_sync / manual

    # SHELTER
    bed_used:       Optional[int]  = None
    bed_total:      Optional[int]  = None
    srt:            Optional[dict] = None
    pending_intake: Optional[int]  = None
    cmist_pending:  Optional[int]  = None
    staff_on_duty:  Optional[int]  = None

    # MEDICAL
    casualties:      Optional[dict] = None
    waiting_count:   Optional[int]  = None
    pending_evac:    Optional[int]  = None
    evacuated_total: Optional[int]  = None
    supplies:        Optional[dict] = None

    # FORWARD
    units: Optional[list] = None

    # SECURITY
    post_total:      Optional[int] = None
    post_anomaly:    Optional[str] = None
    qrf_available:   Optional[int] = None
    isolation_count: Optional[int] = None

    vehicle_available: Optional[int]  = None
    extra:             Optional[dict] = None

    class Config:
        extra = "allow"
