from pydantic import BaseModel
from typing import Optional


class ExerciseCreateIn(BaseModel):
    name:              str
    type:              str = "ttx"    # 'real' | 'ttx'
    date:              Optional[str] = None
    location:          Optional[str] = None
    scenario_summary:  Optional[str] = None
    weather:           Optional[str] = None
    participant_count: Optional[int] = None
    organizing_body:   Optional[str] = None
    # TTX 專屬
    facilitator:  Optional[str] = None
    scenario_id:  Optional[str] = None


class ExerciseStatusIn(BaseModel):
    status: str  # 'setup' | 'active' | 'archived'


class AAREntryIn(BaseModel):
    category: str    # 'well' | 'improve' | 'recommend'
    content:  str
    created_by: Optional[str] = None
