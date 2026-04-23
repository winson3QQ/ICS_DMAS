from typing import Optional
from fastapi import APIRouter, HTTPException
from repositories.decision_repo import create_decision, get_decisions, decide
from schemas.decision import DecisionIn, DecideIn

router = APIRouter(prefix="/api/decisions", tags=["裁示"])


@router.post("")
def post_decision(dec: DecisionIn):
    return create_decision(dec.model_dump(), dec.exercise_id)


@router.get("")
def get_dec(status: Optional[str] = None):
    return get_decisions(status)


@router.post("/{decision_id}/decide")
def do_decide(decision_id: str, body: DecideIn):
    try:
        return decide(decision_id, body.action, body.decided_by, body.execution_note)
    except ValueError as e:
        raise HTTPException(400, str(e))
