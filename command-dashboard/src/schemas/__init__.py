"""
schemas/ — 所有 Pydantic request/response 模型集中管理
"""

from .snapshot  import SnapshotIn
from .event     import EventIn, EventPatch, DeadlinePatch, EventNoteIn
from .decision  import DecisionIn, DecideIn
from .sync      import SyncPushIn, ConflictResolveIn
from .auth      import LoginIn
from .admin     import (AccountCreateIn, AccountStatusIn, PinResetIn,
                        AdminPinIn, RoleUpdateIn, PiNodeCreateIn, ConfigIn)
from .manual    import ManualRecordIn
from .exercise  import ExerciseCreateIn, ExerciseStatusIn, AAREntryIn
from .ttx       import TTXInjectBulkIn
from .ai        import AIRecommendIn

__all__ = [
    "SnapshotIn",
    "EventIn", "EventPatch", "DeadlinePatch", "EventNoteIn",
    "DecisionIn", "DecideIn",
    "SyncPushIn", "ConflictResolveIn",
    "LoginIn",
    "AccountCreateIn", "AccountStatusIn", "PinResetIn",
    "AdminPinIn", "RoleUpdateIn", "PiNodeCreateIn", "ConfigIn",
    "ManualRecordIn",
    "ExerciseCreateIn", "ExerciseStatusIn", "AAREntryIn",
    "TTXInjectBulkIn",
    "AIRecommendIn",
]
