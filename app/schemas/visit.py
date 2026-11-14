"""Skema request/response Registrasi Kunjungan (kontrak 6.1)."""

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VisitCreate(BaseModel):
    patient_id: uuid.UUID
    service_id: int
    visit_date: date
    sesi: Literal["pagi_siang", "sore_malam"]
    keluhan: str | None = Field(default=None, max_length=1000)


class ServiceRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str


class VisitCreated(BaseModel):
    """Response 201 booking — bentuk persis sesuai kontrak 6.1."""

    id: uuid.UUID
    patient_id: uuid.UUID
    service: ServiceRef
    visit_date: date
    sesi: str
    queue_number: int
    status: str
