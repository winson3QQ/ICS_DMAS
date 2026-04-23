from pydantic import BaseModel
from typing import Optional


class EventIn(BaseModel):
    reported_by_unit:         str
    event_type:               str
    severity:                 str = "info"
    description:              str
    operator_name:            str
    location_desc:            Optional[str] = None
    location_zone_id:         Optional[str] = None
    response_type:            Optional[str] = None
    needs_commander_decision: bool = False
    related_person_name:      Optional[str] = None
    assigned_unit:            Optional[str] = None
    occurred_at:              Optional[str] = None
    session_type:             str = "real"
    exercise_id:              Optional[int] = None  # C0：關聯演練


class EventPatch(BaseModel):
    assigned_unit:   Optional[str] = None
    location_desc:   Optional[str] = None
    location_zone_id: Optional[str] = None


class DeadlinePatch(BaseModel):
    delta_minutes: int
    operator:      str


class EventNoteIn(BaseModel):
    text:     str
    operator: str
