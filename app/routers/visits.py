"""Router Registrasi Kunjungan (kontrak 6.1). Get/daftar kunjungan menyusul."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_role
from app.db import SessionDep
from app.models import User
from app.schemas.visit import VisitCreate, VisitCreated
from app.services import visit_service

PasienOnly = Annotated[User, Depends(require_role("pasien"))]

router = APIRouter(tags=["kunjungan"])


@router.post("/visits", response_model=VisitCreated, status_code=201)
async def create_visit(
    payload: VisitCreate, session: SessionDep, user: PasienOnly
) -> VisitCreated:
    """Booking kunjungan + nomor antrean atomik (next_queue_number)."""
    visit, service = await visit_service.create_visit(session, user, payload)
    return VisitCreated(
        id=visit.id,
        patient_id=visit.patient_id,
        service=service,
        visit_date=visit.visit_date,
        sesi=visit.sesi,
        queue_number=visit.queue_number,
        status=visit.status,
    )
