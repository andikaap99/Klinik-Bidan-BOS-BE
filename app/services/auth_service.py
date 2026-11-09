"""Logika akun: register (publik), login, ubah profil/password sendiri.

Aturan kontrak:
- Register adalah satu-satunya cara membuat akun pasien (selalu role=pasien).
- Pesan error login tidak membedakan username salah / password salah.
- Password hanya bisa diubah pemilik akun atau lewat reset admin.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import MeUpdate, PasswordChange, RegisterRequest


def _register_shape(user: User) -> dict:
    """Bentuk ringkas response register sesuai contoh kontrak."""
    return {
        "id": user.id,
        "username": user.username,
        "nama_lengkap": user.nama_lengkap,
        "role": user.role,
    }


async def register_account(session: AsyncSession, data: RegisterRequest) -> User:
    """Buat akun pasien. Transaksi pendek: hanya cek unik + insert."""
    async with session.begin():
        existing = await session.scalar(
            select(User).where(func.lower(User.username) == data.username.lower())
        )
        if existing is not None:
            raise ApiError(
                code="USERNAME_TAKEN",
                message="Username sudah dipakai, pilih yang lain",
                status_code=409,
            )
        user = User(
            username=data.username,
            password_hash=hash_password(data.password),
            role="pasien",  # register publik selalu pasien; role tak bisa dikirim klien
            nama_lengkap=data.nama_lengkap,
            nomor_wa=data.nomor_wa,
        )
        session.add(user)
        try:
            await session.flush()
        except IntegrityError as exc:
            # Race dua request username sama bersamaan; index unique menahan
            raise ApiError(
                code="USERNAME_TAKEN", message="Username sudah dipakai", status_code=409
            ) from exc
    return user


async def authenticate(session: AsyncSession, username: str, password: str) -> User:
    """Login. Pesan error tidak membedakan username salah / password salah."""
    user = await session.scalar(
        select(User).where(func.lower(User.username) == username.lower())
    )
    if user is None or not verify_password(password, user.password_hash):
        raise ApiError(
            code="INVALID_CREDENTIALS",
            message="Username atau password salah",
            status_code=401,
        )
    return user


def issue_token(user: User) -> tuple[str, int]:
    """Buat token JWT + expires_in (detik). Kontrak: expires_in 3600 untuk 60 menit."""
    token = create_access_token(user.id, user.role)
    return token, get_settings().access_token_expire_minutes * 60


async def update_profile(session: AsyncSession, user: User, payload: MeUpdate) -> User:
    """PATCH /me. Hanya field yang dikirim yang diperbarui (exclude_unset)."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user


async def change_password(session: AsyncSession, user: User, payload: PasswordChange) -> None:
    """Ganti password sendiri; 403 bila password lama tidak cocok."""
    if not verify_password(payload.password_lama, user.password_hash):
        raise ApiError(
            code="FORBIDDEN",
            message="Password lama tidak sesuai",
            status_code=403,
        )
    user.password_hash = hash_password(payload.password_baru)
    await session.commit()
