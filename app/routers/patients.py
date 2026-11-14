"""Router Profil Pasien (kontrak bagian 4)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.security import CurrentUser, require_role
from app.db import SessionDep
from app.models import User
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientOut,
    PatientUpdate,
)
from app.services import patient_service

# Endpoint khusus pasien (kontrak: bidan tidak mendaftar profil)
PasienOnly = Annotated[User, Depends(require_role("pasien"))]

router = APIRouter(tags=["pasien"])


@router.get("/patients", response_model=PatientListResponse)
async def list_patients(
    session: SessionDep,
    user: PasienOnly,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PatientListResponse:
    """Daftar pasien milik akun yang login."""
    return await patient_service.list_patients(session, user, limit, offset)


@router.post("/patients", response_model=PatientOut, status_code=201)
async def create_patient(
    payload: PatientCreate, session: SessionDep, user: PasienOnly
) -> PatientOut:
    """Tambah profil pasien. Backend mencari dulu sebelum membuat (kontrak 4.2)."""
    patient = await patient_service.create_patient(session, user, payload)
    return PatientOut.model_validate(patient)


@router.get("/patients/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id, session: SessionDep, user: CurrentUser
) -> PatientOut:
    """Detail: pasien (pemilik) atau bidan (baca). Bukan pemilik: 404."""
    patient = await patient_service.get_patient(session, user, patient_id)
    return PatientOut.model_validate(patient)


@router.patch("/patients/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id, payload: PatientUpdate, session: SessionDep, user: CurrentUser
) -> PatientOut:
    """Ubah profil sendiri. NIK tidak bisa diubah; bidan 403."""
    patient = await patient_service.update_patient(session, user, patient_id, payload)
    return PatientOut.model_validate(patient)
