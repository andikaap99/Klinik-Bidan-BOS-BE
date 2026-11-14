"""Router Layanan (kontrak bagian 5): GET /services, read-only.

Tambah/ubah layanan tidak tersedia (kontrak) — master di-seed via migrasi.
"""

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.security import CurrentUser
from app.db import SessionDep
from app.models import Service
from app.schemas.service import ServiceListResponse, ServiceOut, ServiceOutBidan

router = APIRouter(tags=["layanan"])

# Role yang melihat durasi (kontrak: bidan). Admin ikut bila sudah aktif.
_DURATION_ROLES = {"bidan", "admin"}


@router.get("/services", response_model=ServiceListResponse)
async def list_services(
    session: SessionDep,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ServiceListResponse:
    """Semua yang login. Pasien: {id, kode, nama}. Bidan: + avg_duration_minutes."""
    total = await session.scalar(select(func.count()).select_from(Service))
    services = (
        await session.scalars(select(Service).order_by(Service.id).limit(limit).offset(offset))
    ).all()

    items: list[ServiceOutBidan | ServiceOut] = []
    if user.role in _DURATION_ROLES:
        items = [ServiceOutBidan.model_validate(s) for s in services]
    else:
        items = [ServiceOut.model_validate(s) for s in services]

    return ServiceListResponse(items=items, total=total, limit=limit, offset=offset)
