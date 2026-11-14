"""Skema response daftar layanan (kontrak bagian 5)."""

from pydantic import BaseModel, ConfigDict


class ServiceOut(BaseModel):
    """Bentuk ringkas untuk semua role (pasien tidak melihat durasi)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str
    nama: str


class ServiceOutBidan(ServiceOut):
    """Untuk bidan: ditambah durasi estimasi (0 = belum ditentukan)."""

    avg_duration_minutes: int


class ServiceListResponse(BaseModel):
    """Pagination sesuai ketentuan umum: limit default 20, maksimal 100."""

    items: list[ServiceOutBidan | ServiceOut]
    total: int
    limit: int
    offset: int
