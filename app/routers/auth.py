"""Router Auth & Akun (kontrak bagian 3): /register, /login, /me, /me/password."""

from fastapi import APIRouter

from app.core.security import CurrentUser
from app.db import SessionDep
from app.schemas.auth import (
    AuthUser,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    MeUpdate,
    PasswordChange,
    RegisterRequest,
    RegisterResponse,
)
from app.services import auth_service

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(payload: RegisterRequest, session: SessionDep) -> RegisterResponse:
    """Publik. Satu-satunya cara membuat akun pasien (role selalu pasien)."""
    user = await auth_service.register_account(session, payload)
    return RegisterResponse(
        id=user.id,
        username=user.username,
        nama_lengkap=user.nama_lengkap,
        role=user.role,
    )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, session: SessionDep) -> LoginResponse:
    """Publik. Mengembalikan access_token (tanpa refresh token, sesuai arsitektur)."""
    user = await auth_service.authenticate(session, payload.username, payload.password)
    token, expires_in = auth_service.issue_token(user)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=AuthUser.model_validate(user),
    )


@router.get("/me", response_model=AuthUser)
async def me(user: CurrentUser) -> AuthUser:
    """Semua role. Rincian akun sendiri."""
    return AuthUser.model_validate(user)


@router.patch("/me", response_model=AuthUser)
async def update_me(
    payload: MeUpdate, user: CurrentUser, session: SessionDep
) -> AuthUser:
    """Semua role. Hanya nama_lengkap / nomor_wa; username dan role tak bisa diubah."""
    updated = await auth_service.update_profile(session, user, payload)
    return AuthUser.model_validate(updated)


@router.post("/me/password", response_model=MessageResponse)
async def change_password(
    payload: PasswordChange, user: CurrentUser, session: SessionDep
) -> MessageResponse:
    """Semua role. Satu-satunya cara pengguna mengganti password sendiri."""
    await auth_service.change_password(session, user, payload)
    return MessageResponse(message="Password berhasil diubah")
