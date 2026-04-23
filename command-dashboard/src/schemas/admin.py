from pydantic import BaseModel
from typing import Optional


class AccountCreateIn(BaseModel):
    username:     str
    pin:          str
    role:         str = "操作員"
    role_detail:  Optional[str] = None
    display_name: Optional[str] = None


class AccountStatusIn(BaseModel):
    status: str  # active / suspended


class PinResetIn(BaseModel):
    new_pin: str


class AdminPinIn(BaseModel):
    new_pin: str


class RoleUpdateIn(BaseModel):
    role:        str
    role_detail: Optional[str] = None


class PiNodeCreateIn(BaseModel):
    unit_id: str
    label:   str


class ConfigIn(BaseModel):
    value: str
