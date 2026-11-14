"""Logika Profil Pasien (kontrak bagian 4).

Aturan:
- Satu akun bisa punya banyak profil; satu profil dimiliki satu akun.
- Backend mencari dulu sebelum membuat baru: NIK untuk dewasa, kombinasi
  nama + tanggal lahir + penanggung jawab untuk bayi. Duplikat -> 409
  PATIENT_EXISTS dengan pesan umum (tidak membocorkan pemilik data).
- NIK tidak bisa diubah lewat endpoint; bidan tidak bisa mengubah profil.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models import Patient, User
from app.schemas.patient import PatientCreate, PatientItem, PatientListResponse, PatientUpdate

_EXISTS_MESSAGE = "Data sudah terdaftar, hubungi klinik"
_NOT_FOUND_MESSAGE = "Pasien tidak ditemukan"
_FORBIDDEN_UPDATE_MESSAGE = "Bidan tidak bisa mengubah profil pasien"


def _patient_not_found() -> ApiError:
    return ApiError(code="NOT_FOUND", message=_NOT_FOUND_MESSAGE, status_code=404)


async def _check_duplicate(session: AsyncSession, data: PatientCreate) -> None:
    """Deteksi duplikat lintas akun sebelum insert (kontrak 4.2)."""
    if data.nik:
        existing = await session.scalar(select(Patient).where(Patient.nik == data.nik))
    else:
        # Aturan bayi: nama + tanggal lahir + penanggung jawab (nama tak peka huruf besar)
        existing = await session.scalar(
            select(Patient).where(
                func.lower(Patient.nama_lengkap) == data.nama_lengkap.lower(),
                Patient.tanggal_lahir == data.tanggal_lahir,
                func.coalesce(Patient.nama_penanggung_jawab, "")
                == (data.nama_penanggung_jawab or ""),
            )
        )
    if existing is not None:
        raise ApiError(
            code="PATIENT_EXISTS", message=_EXISTS_MESSAGE, status_code=409
        )


async def list_patients(
    session: AsyncSession, user: User, limit: int, offset: int
) -> PatientListResponse:
    if user.role != "pasien":
        raise ApiError(
            code="FORBIDDEN", message="Hanya pasien yang punya profil sendiri", status_code=403
        )
    base = select(Patient).where(
        Patient.user_id == user.id,
        Patient.deleted_at.is_(None),
        Patient.merged_into_id.is_(None),
    )
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    patients = (
        await session.scalars(
            base.order_by(Patient.created_at, Patient.id).limit(limit).offset(offset)
        )
    ).all()
    return PatientListResponse(
        items=[PatientItem.model_validate(p) for p in patients],
        total=total,
        limit=limit,
        offset=offset,
    )


async def create_patient(session: AsyncSession, user: User, data: PatientCreate) -> Patient:
    if user.role != "pasien":
        raise ApiError(
            code="FORBIDDEN", message="Hanya pasien yang bisa mendaftarkan profil", status_code=403
        )
    await _check_duplicate(session, data)
    patient = Patient(user_id=user.id, **data.model_dump())
    session.add(patient)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Race: unique index NIK menahan dua request NIK sama bersamaan
        raise ApiError(code="PATIENT_EXISTS", message=_EXISTS_MESSAGE, status_code=409) from exc
    await session.refresh(patient)
    return patient


async def _get_visible(session: AsyncSession, patient_id, user: User) -> Patient:
    """Detail: pemilik atau bidan (baca). Bukan pemilik / sudah hapus/merge -> 404."""
    patient = await session.get(Patient, patient_id)
    if (
        patient is None
        or patient.deleted_at is not None
        or patient.merged_into_id is not None
        or (user.role != "bidan" and patient.user_id != user.id)
    ):
        raise _patient_not_found()
    return patient


async def get_patient(session: AsyncSession, user: User, patient_id) -> Patient:
    return await _get_visible(session, patient_id, user)


async def update_patient(
    session: AsyncSession, user: User, patient_id, data: PatientUpdate
) -> Patient:
    patient = await _get_visible(session, patient_id, user)
    if user.role == "bidan":
        # Kontrak: bidan hanya baca; perubahan profil khusus pemilik
        raise ApiError(code="FORBIDDEN", message=_FORBIDDEN_UPDATE_MESSAGE, status_code=403)
    if patient.user_id != user.id:
        raise _patient_not_found()
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    await session.commit()
    await session.refresh(patient)
    return patient
