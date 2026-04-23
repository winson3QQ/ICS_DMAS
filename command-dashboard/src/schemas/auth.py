from pydantic import BaseModel


class LoginIn(BaseModel):
    username: str
    pin:      str
