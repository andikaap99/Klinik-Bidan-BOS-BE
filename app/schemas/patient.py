"""Skema request/response Profil Pasien (kontrak bagian 4)."""

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_WA_PATTERN = r"^(\+62|62|0)8[0-9]{8,12}$"
_NIK_PATTERN = r"^[0-9]{16}$"


class PatientCreate(BaseModel):
    """Wajib: nama_lengkap, tanggal_lahir, jenis_kelamin. Lainnya opsional."""

    nik: str | None = Field(default=None, pattern=_NIK_PATTERN)
    nama_lengkap: str = Field(min_length=1, max_length=100)
    tanggal_lahir: date
    jenis_kelamin: Literal["L", "P"]
    nama_penanggung_jawab: str | None = Field(default=None, min_length=1, max_length=100)
    nomor_wa: str | None = Field(default=None, pattern=_WA_PATTERN)
    alamat: str | None = Field(default=None, max_length=300)


class PatientUpdate(BaseModel):
    """PATCH — NIK tidak bisa diubah (tidak ada di sini)."""

    nama_lengkap: str | None = Field(default=None, min_length=1, max_length=100)
    tanggal_lahir: date | None = None
    jenis_kelamin: Literal["L", "P"] | None = None
    nama_penanggung_jawab: str | None = Field(default=None, min_length=1, max_length=100)
    nomor_wa: str | None = Field(default=None, pattern=_WA_PATTERN)
    alamat: str | None = Field(default=None, max_length=300)


class PatientOut(BaseModel):
    """Objek Pasien (lengkap) — tanpa data internal (user_id, deleted_at, merge)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no_rm: str
    nik: str | None
    nama_lengkap: str
    tanggal_lahir: date
    jenis_kelamin: str
    nama_penanggung_jawab: str | None
    nomor_wa: str | None
    alamat: str | None


class PatientItem(BaseModel):
    """Bentuk ringkas untuk daftar (kontrak 4.1)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no_rm: str
    nama_lengkap: str
    tanggal_lahir: date
    jenis_kelamin: str
    nama_penanggung_jawab: str | None


class PatientListResponse(BaseModel):
    items: list[PatientItem]
    total: int
    limit: int
    offset: int
