from pydantic import BaseModel
from typing import Optional


class ManualRecordIn(BaseModel):
    form_id:    str
    operator:   str
    summary:    str
    payload:    dict
    device_id:  Optional[str] = None
    exercise_id: Optional[int] = None  # C0

    class Config:
        extra = "allow"
