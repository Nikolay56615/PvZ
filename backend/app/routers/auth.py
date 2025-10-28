from fastapi import APIRouter, Depends, HTTPException
from ..schemas.auth import LoginIn, TokenOut
from ..auth import User, make_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn):
    if payload.username == "admin" and payload.password == "admin":
        user = User(user_id="00000000-0000-0000-0000-000000000001", name="admin", tenant_id="fake", permissions="ADMIN")
        return TokenOut(access_token=await make_token(user))
    raise HTTPException(401, "Invalid credentials")