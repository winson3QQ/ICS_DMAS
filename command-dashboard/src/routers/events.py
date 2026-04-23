from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request
from auth.service import validate_session
from repositories.event_repo import (
    create_event, get_events, patch_event, update_event_status, add_event_note
)
from repositories.decision_repo import create_decision
from schemas.event import EventIn, EventPatch, DeadlinePatch, EventNoteIn

router = APIRouter(prefix="/api/events", tags=["事件"])

VALID_SEVERITIES = {"info", "warning", "critical"}
VALID_UNITS      = {"shelter", "medical", "forward", "security", "command"}


@router.post("")
def post_event(ev: EventIn):
    if ev.severity not in VALID_SEVERITIES:
        raise HTTPException(422, f"severity 必須是 {VALID_SEVERITIES}")
    if ev.reported_by_unit not in VALID_UNITS:
        raise HTTPException(422, f"reported_by_unit 必須是 {VALID_UNITS}")
    result = create_event(ev.model_dump(), ev.exercise_id)
    if ev.needs_commander_decision:
        create_decision({
            "primary_event_id":   result["id"],
            "decision_type":      "initial",
            "severity":           ev.severity if ev.severity != "info" else "warning",
            "decision_title":     ev.description[:60],
            "impact_description": f"來源：{ev.reported_by_unit}　{ev.event_type}",
            "suggested_action_a": "（計劃情報組補充建議動作）",
            "created_by":         ev.operator_name,
        }, ev.exercise_id)
    return result


@router.get("")
def get_ev(status: Optional[str] = None, limit: int = 50):
    return get_events(status, limit)


@router.patch("/{event_id}")
def patch_ev(event_id: str, body: EventPatch):
    updates = {}
    if body.assigned_unit is not None:
        updates["assigned_unit"]    = body.assigned_unit or None
    if body.location_desc is not None:
        updates["location_desc"]    = body.location_desc
    if body.location_zone_id is not None:
        updates["location_zone_id"] = body.location_zone_id
    if updates:
        patch_event(event_id, updates)
    return {"ok": True}


@router.patch("/{event_id}/deadline")
def patch_deadline(event_id: str, body: DeadlinePatch):
    events = get_events()
    ev = next((e for e in events if e["id"] == event_id), None)
    if not ev:
        raise HTTPException(404, "event not found")
    current = ev.get("response_deadline")
    base    = (datetime.fromisoformat(current.replace("Z", "+00:00"))
               if current else datetime.now(timezone.utc))
    new_dl  = (base + timedelta(minutes=body.delta_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    patch_event(event_id, {"response_deadline": new_dl})
    return {"ok": True, "new_deadline": new_dl}


@router.patch("/{event_id}/status")
def patch_status(event_id: str, status: str, operator: str):
    try:
        update_event_status(event_id, status, operator)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.post("/{event_id}/notes")
def add_note(event_id: str, body: EventNoteIn):
    try:
        return add_event_note(event_id, body.text, body.operator)
    except ValueError as e:
        raise HTTPException(404, str(e))
