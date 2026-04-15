from __future__ import annotations

import logging
import os
from dataclasses import asdict

import httpx
import jwt
from asyncpg import UniqueViolationError
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
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
    title="Backend Service",
    description="Authentication + training CRUD API",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database = Database()
JUDGE_SERVICE_URL = os.getenv("JUDGE_SERVICE_URL")


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


class SessionListItemResponse(BaseModel):
    session_id: str
    room_name: str
    product: str
    owner_user_id: str
    started_at: str | None = None
    ended_at: str | None = None
    total_score: float | None = None
    judge_ready: bool = False
    scenario_id: str | None = None


class TrainingScenarioUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    persona_description: str = Field(min_length=1)
    main_pain: str = Field(min_length=1)


class TrainingScenarioResponse(BaseModel):
    id: str
    name: str
    persona_description: str
    main_pain: str
    created_by_user_id: str
    created_at: str | None = None
    updated_at: str | None = None


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
    logger.info("Backend service started successfully")


@app.on_event("shutdown")
async def shutdown() -> None:
    await database.close()


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "backend-service",
        "status": "running",
        "version": "0.2.0",
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


@app.get("/api/sessions", response_model=list[SessionListItemResponse])
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: AuthUserResponse = Depends(get_current_user),
) -> list[SessionListItemResponse]:
    rows = await database.list_sessions_for_actor(
        user_id=current_user.user_id,
        role=current_user.role,
        limit=limit,
    )
    return [SessionListItemResponse(**asdict(row)) for row in rows]


@app.get("/api/training-scenarios", response_model=list[TrainingScenarioResponse])
async def list_training_scenarios(
    _: AuthUserResponse = Depends(get_current_user),
) -> list[TrainingScenarioResponse]:
    rows = await database.list_training_scenarios()
    return [TrainingScenarioResponse(**asdict(row)) for row in rows]


@app.post("/api/training-scenarios", response_model=TrainingScenarioResponse)
async def create_training_scenario(
    request: TrainingScenarioUpsertRequest,
    current_user: AuthUserResponse = Depends(require_coach),
) -> TrainingScenarioResponse:
    row = await database.create_training_scenario(
        name=request.name,
        persona_description=request.persona_description,
        main_pain=request.main_pain,
        created_by_user_id=current_user.user_id,
    )
    return TrainingScenarioResponse(**asdict(row))


@app.put("/api/training-scenarios/{scenario_id}", response_model=TrainingScenarioResponse)
async def update_training_scenario(
    scenario_id: str,
    request: TrainingScenarioUpsertRequest,
    _: AuthUserResponse = Depends(require_coach),
) -> TrainingScenarioResponse:
    row = await database.update_training_scenario(
        scenario_id=scenario_id,
        name=request.name,
        persona_description=request.persona_description,
        main_pain=request.main_pain,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Training scenario not found")
    return TrainingScenarioResponse(**asdict(row))


@app.get("/api/session-results")
async def get_session_results(
    session_id: str | None = Query(default=None),
    room_name: str | None = Query(default=None),
    refresh: bool = Query(default=False),
    _: AuthUserResponse = Depends(get_current_user),
) -> Response:
    if not JUDGE_SERVICE_URL:
        raise HTTPException(status_code=500, detail="JUDGE_SERVICE_URL is not defined")
    if not room_name and not session_id:
        raise HTTPException(status_code=400, detail="room_name or session_id is required")
    if room_name and session_id:
        raise HTTPException(status_code=400, detail="Provide only one of room_name or session_id")

    judge_url = httpx.URL(f"{JUDGE_SERVICE_URL.rstrip('/')}/api/session-results")
    params: dict[str, str] = {}
    if session_id:
        params["session_id"] = session_id
    if room_name:
        params["room_name"] = room_name
    if refresh:
        params["refresh"] = "true"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            upstream = await client.get(str(judge_url), params=params)
    except httpx.HTTPError as exc:
        logger.exception("Failed to call judge service for session results")
        raise HTTPException(status_code=502, detail="Failed to reach judge service") from exc

    content_type = upstream.headers.get("content-type", "application/json")
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=content_type.split(";", 1)[0],
        headers={"Cache-Control": "no-store"},
    )
