from pydantic import BaseModel


class AuthPass(BaseModel):
    username: str | None = None
    email: str | None = None
class LoginIn(BaseModel):
    user: AuthPass
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"