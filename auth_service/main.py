from __future__ import annotations

import logging

import jwt
from asyncpg import UniqueViolationError
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from database import Database
from security import create_access_token, decode_access_token, hash_password, verify_password

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Auth Service",
    description="Local authentication service for manager/coach access",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database = Database()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthUserResponse(BaseModel):
    user_id: str
    email: EmailStr
    role: str


class LoginResponse(BaseModel):
    access_token: str
    user: AuthUserResponse


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return token


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> AuthUserResponse:
    token = _extract_bearer_token(authorization)
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user = await database.get_user_by_id(payload["user_id"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return AuthUserResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


def require_coach(current_user: AuthUserResponse = Depends(get_current_user)) -> AuthUserResponse:
    if current_user.role != "coach":
        raise HTTPException(status_code=403, detail="Coach role is required")
    return current_user


@app.on_event("startup")
async def startup() -> None:
    await database.initialize()
    logger.info("Auth service started successfully")


@app.on_event("shutdown")
async def shutdown() -> None:
    await database.close()


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "auth-service",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    user = await database.get_user_by_email(request.email)
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    user_response = AuthUserResponse(user_id=user.id, email=user.email, role=user.role)
    return LoginResponse(access_token=token, user=user_response)


@app.post("/api/auth/register", response_model=LoginResponse)
async def register(request: LoginRequest) -> LoginResponse:
    existing = await database.get_user_by_email(request.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    created = await database.create_user(
        email=request.email,
        password_hash=hash_password(request.password),
        role="manager",
    )
    token = create_access_token(user_id=created.id, email=created.email, role=created.role)
    user_response = AuthUserResponse(user_id=created.id, email=created.email, role=created.role)
    return LoginResponse(access_token=token, user=user_response)


@app.post("/api/auth/logout")
async def logout() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/me", response_model=AuthUserResponse)
async def me(current_user: AuthUserResponse = Depends(get_current_user)) -> AuthUserResponse:
    return current_user


@app.get("/api/auth/users", response_model=list[AuthUserResponse])
async def list_users(_: AuthUserResponse = Depends(require_coach)) -> list[AuthUserResponse]:
    users = await database.list_users()
    return [
        AuthUserResponse(user_id=user.id, email=user.email, role=user.role)
        for user in users
    ]


@app.post("/api/auth/users", response_model=AuthUserResponse)
async def create_user(
    request: CreateUserRequest,
    _: AuthUserResponse = Depends(require_coach),
) -> AuthUserResponse:
    if request.role not in {"manager", "coach"}:
        raise HTTPException(status_code=400, detail="Role must be manager or coach")

    try:
        user = await database.create_user(
            email=request.email,
            password_hash=hash_password(request.password),
            role=request.role,
        )
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="User with this email already exists") from exc

    return AuthUserResponse(user_id=user.id, email=user.email, role=user.role)
