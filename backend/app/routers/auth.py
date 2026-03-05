from fastapi import APIRouter, HTTPException, Depends
from ..schemas.auth import LoginIn, TokenOut
from ..auth import User, make_token
from ..deps import db_conn
from ..repositories.auth import verify_user_credentials, create_user, pwd_context, get_user_by_username, get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, conn=Depends(db_conn)):
    user_pass = payload.user
    username = user_pass.username
    email = user_pass.email

    user_row = await verify_user_credentials(conn, username=username, email=email, password=payload.password)
    if not user_row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = User(
        user_id=str(user_row.get("user_id")),
        name=user_row.get("name"),
            tenant_id=(str(user_row.get("tenant_id")) if user_row.get("tenant_id") else None),
        permissions=str(user_row.get("permissions")) if user_row.get("permissions") else "VIEWER",
    )

    return TokenOut(access_token=make_token(user))


@router.post("/register", response_model=TokenOut)
async def register(payload: LoginIn, conn=Depends(db_conn)):
    user_pass = payload.user
    username = user_pass.username or user_pass.email
    email = user_pass.email or None

    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Invalid registration data")

    existing = await get_user_by_username(conn, username=username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    if email:
        existing_email = await get_user_by_email(conn, email=email)
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already exists")

    hashed = pwd_context.hash(payload.password)
    try:
        created = await create_user(conn, username=username, email=email, hashed_password=hashed)
    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(status_code=409, detail="User already exists")

    user = User(
        user_id=str(created.get("user_id")),
        name=created.get("name"),
            tenant_id=(str(created.get("tenant_id")) if created.get("tenant_id") else None),
        permissions=str(created.get("permissions")) if created.get("permissions") else "VIEWER",
    )

    return TokenOut(access_token=make_token(user))