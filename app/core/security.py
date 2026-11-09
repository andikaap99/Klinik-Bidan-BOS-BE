"""Keamanan: hash password (argon2), JWT access token, dependency auth & RBAC.

Aturan arsitektur:
- Tanpa refresh token — cukup JWT dengan expiry (default 1 jam).
- Prinsip keamanan: reply tidak membedakan "username salah" vs "password salah".
- Role diambil dari token, bukan dari data klien; namun otorisasi sensitif
  (mis. ubah rekam medis) tetap memverifikasi kepemilikan di database.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.errors import ApiError
from app.db import SessionDep
from app.models import User

# PasswordHash.recommended() = argon2id
pwd_context = PasswordHash.recommended()

_bearer = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    return pwd_context.verify(plain, password_hash)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> tuple[uuid.UUID, str]:
    """Validasi + dekode token -> (user_id, role). Raise ApiError bila tidak valid."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(
            code="TOKEN_EXPIRED", message="Token kedaluwarsa, silakan login ulang", status_code=401
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise ApiError(
            code="INVALID_CREDENTIALS", message="Token tidak valid", status_code=401
        ) from exc

    try:
        user_id = uuid.UUID(payload["sub"])
        role = payload["role"]
    except (KeyError, ValueError) as exc:
        raise ApiError(
            code="INVALID_CREDENTIALS", message="Token tidak valid", status_code=401
        ) from exc
    return user_id, role


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
) -> User:
    """Ambil user dari Bearer token. Role konsisten dengan DB (sumber kebenaran)."""

    if credentials is None:
        raise ApiError(
            code="INVALID_CREDENTIALS",
            message="Header Authorization: Bearer <access_token> wajib ada",
            status_code=401,
        )
    user_id, _ = decode_access_token(credentials.credentials)

    user = await session.get(User, user_id)
    if user is None:
        # Token sah tapi user hilang (tidak seharusnya terjadi: akun permanen)
        raise ApiError(
            code="INVALID_CREDENTIALS", message="Token tidak valid", status_code=401
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: str):
    """Dependency RBAC: cek role dari token/user di endpoint yang membatasi role."""

    async def _check(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise ApiError(
                code="FORBIDDEN",
                message="Role tidak diizinkan untuk endpoint ini",
                status_code=403,
            )
        return user

    return _check