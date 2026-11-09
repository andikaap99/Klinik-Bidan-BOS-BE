from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import ApiError
from app.db import SessionDep

# asyncpg bisa melepas ConnectionRefusedError mentah (OSError) saat koneksi gagal,
# versi SQLAlchemy ini me-re-raise tanpa dibungkus jadi DBAPIError.
_HEALTHY_ERRORS = (SQLAlchemyError, OSError)

router = APIRouter(tags=["sistem"])


@router.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    """Publik. Dipakai pemantauan server dan Compose healthcheck di tumpukan penuh.

    DB aktif  -> 200 {"status": "ok", "db": "ok"}
    DB mati   -> 503 {"code": "DB_UNAVAILABLE", ...} agar monitor tidak salah anggap sehat
    """
    try:
        await session.execute(text("SELECT 1"))
    except _HEALTHY_ERRORS as exc:
        raise ApiError(
            code="DB_UNAVAILABLE",
            message="Database tidak tersedia",
            status_code=503,
        ) from exc
    return {"status": "ok", "db": "ok"}
