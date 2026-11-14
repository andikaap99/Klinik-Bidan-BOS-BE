"""Logika Registrasi Kunjungan (kontrak 6.1).

Aturan arsitektur yang wajib:
- Nomor antrean dari `next_queue_number(tanggal, sesi)` di PostgreSQL,
  dipanggil dalam transaksi yang sama dengan INSERT visits, lalu COMMIT.
  Tidak ada operasi lain (jaringan/LLM) di dalamnya.
- Satu pasien tidak boleh mendaftar layanan yang sama dua kali di hari
  yang sama kecuali yang sebelumnya batal (409 VISIT_DUPLICATE).
- Jendela pemesanan: hari ini sampai 7 hari ke depan (keputusan Jira
  2026-11-14), zona Asia/Jakarta.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError
from app.models import Patient, Service, User, Visit
from app.schemas.visit import VisitCreate

_BOOKING_WINDOW_DAYS = 7
_DUPLICATE_MESSAGE = "Pasien sudah terdaftar pada layanan ini di tanggal tersebut"
# Nama constraint partial unique index (pengaman race deteksi duplikat)
_VISIT_DUP_CONSTRAINT = "visits_no_dup_active_uq"


def _today() -> date:
    """'Hari ini' memakai zona aplikasi (Asia/Jakarta), bukan UTC server."""
    return datetime.now(ZoneInfo(get_settings().timezone)).date()


def _validate_booking_window(visit_date: date) -> None:
    today = _today()
    if visit_date < today or visit_date > today + timedelta(days=_BOOKING_WINDOW_DAYS):
        raise ApiError(
            code="VALIDATION_ERROR",
            message=f"Tanggal kunjungan harus hari ini sampai {_BOOKING_WINDOW_DAYS} hari ke depan",
            status_code=422,
        )


def _is_visit_duplicate(exc: IntegrityError) -> bool:
    return _VISIT_DUP_CONSTRAINT in str(exc) or _VISIT_DUP_CONSTRAINT in str(
        getattr(exc, "orig", "")
    )


async def create_visit(
    session: AsyncSession, user: User, data: VisitCreate
) -> tuple[Visit, Service]:
    """Booking. Validasi dulu (read), lalu nomor+INSERT+COMMIT dalam satu tx."""
    # 1. Pasien harus milik akun yang login (selain itu 404, kontrak)
    patient = await session.get(Patient, data.patient_id)
    if (
        patient is None
        or patient.deleted_at is not None
        or patient.merged_into_id is not None
        or patient.user_id != user.id
    ):
        raise ApiError(code="NOT_FOUND", message="Pasien tidak ditemukan", status_code=404)

    # 2. Layanan harus ada
    service = await session.get(Service, data.service_id)
    if service is None:
        raise ApiError(code="NOT_FOUND", message="Layanan tidak ditemukan", status_code=404)

    # 3. Jendela tanggal
    _validate_booking_window(data.visit_date)

    # 4. Duplikat aktif (bukan batal) — cek dulu agar nomor antrean tidak terbakar
    duplicate = await session.scalar(
        select(Visit.id).where(
            Visit.patient_id == data.patient_id,
            Visit.visit_date == data.visit_date,
            Visit.service_id == data.service_id,
            Visit.status != "batal",
        )
    )
    if duplicate is not None:
        raise ApiError(code="VISIT_DUPLICATE", message=_DUPLICATE_MESSAGE, status_code=409)

    # 5. Transaksi pendek: nomor antrean + insert + commit
    queue_number = await session.scalar(
        text("SELECT next_queue_number(:d, CAST(:s AS visit_session))").bindparams(
            d=data.visit_date, s=data.sesi
        )
    )
    visit = Visit(
        patient_id=data.patient_id,
        service_id=service.id,
        visit_date=data.visit_date,
        sesi=data.sesi,
        queue_number=queue_number,
        status="antre",
        keluhan=data.keluhan,
        registered_by=user.id,
    )
    session.add(visit)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Race dua request duplikat bersamaan; unique index menahan.
        # Rollback tx juga mengembalikan counter, nomor tidak terbakar.
        if _is_visit_duplicate(exc):
            raise ApiError(
                code="VISIT_DUPLICATE", message=_DUPLICATE_MESSAGE, status_code=409
            ) from exc
        raise
    await session.refresh(visit)
    return visit, service
