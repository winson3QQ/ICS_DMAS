from pydantic import BaseModel
from typing import Optional


class DecisionIn(BaseModel):
    decision_type:      str   # initial / revision / escalation / closure
    severity:           str   # critical / warning
    decision_title:     str
    impact_description: str
    suggested_action_a: str
    created_by:         str
    suggested_action_b: Optional[str] = None
    primary_event_id:   Optional[str] = None
    parent_decision_id: Optional[str] = None
    exercise_id:        Optional[int] = None  # C0


class DecideIn(BaseModel):
    action:         str   # approved / hold / redirect / completed
    decided_by:     str
    execution_note: str = ""
