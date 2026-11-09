"""Skema request/response area Auth & Akun (kontrak bagian 2-3).

Seluruh response adalah JSON object. Register 201 memakai bentuk ringkas
tanpa nomor_wa sesuai contoh kontrak; /me memakai objek Akun lengkap.
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field

# Variasi nomor WA Indonesia yang diterima: 08..., 62..., +62... (8-20 digit)
_WA_PATTERN = r"^(\+62|62|0)8[0-9]{8,12}$"

# Kontrak tidak menetapkan aturan password; minimum 8 dipilih agar bukan trivial
_PWD_MIN = 8


class RegisterRequest(BaseModel):
    nama_lengkap: str = Field(min_length=1, max_length=100)
    nomor_wa: str | None = Field(default=None, pattern=_WA_PATTERN)
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=_PWD_MIN, max_length=200)


class RegisterResponse(BaseModel):
    """Bentuk ringkas sesuai contoh kontrak (tanpa nomor_wa)."""

    id: uuid.UUID
    username: str
    nama_lengkap: str
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthUser(BaseModel):
    """Objek Akun (dipakai di login dan /me)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    nama_lengkap: str
    nomor_wa: str | None
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


class MeUpdate(BaseModel):
    """PATCH /me — hanya nama_lengkap dan nomor_wa yang boleh berubah."""

    nama_lengkap: str | None = Field(default=None, min_length=1, max_length=100)
    nomor_wa: str | None = Field(default=None, pattern=_WA_PATTERN)


class PasswordChange(BaseModel):
    password_lama: str
    password_baru: str = Field(min_length=_PWD_MIN, max_length=200)


class MessageResponse(BaseModel):
    message: str
