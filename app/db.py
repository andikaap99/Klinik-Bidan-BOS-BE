"""Koneksi database (SQLAlchemy 2.0 async + asyncpg).

Aturan penting dari konteks arsitektur:
- API async; cron job forecast boleh sync (psycopg) memakai model yang sama.
- Transaksi pendaftaran kunjungan harus pendek: dibuka saat submit dengan
  `async with session.begin()`, hanya operasi DB di dalamnya, lalu COMMIT.
- Timezone PostgreSQL di-set ke Asia/Jakarta per koneksi agar WHENEVER
  `CURRENT_DATE`/`now()` di view dan query selalu "hari ini" Jakarta.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.db_echo,
            pool_pre_ping=True,
            connect_args={
                "server_settings": {
                    "timezone": settings.timezone,
                    "application_name": "dss_klinik_api",
                }
            },
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        # expire_on_commit=False agar hasil query tetap dipakai setelah commit
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def dispose_engine() -> None:
    """Dipanggil saat shutdown (dan antar test) supaya koneksi tidak bocor."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependency FastAPI: satu session per request.

    Pembacaan bisa langsung memakai session. Tulisan yang butuh transaksi
    eksplisit (mis. pendaftaran kunjungan) membuka `session.begin()` sendiri
    di service agar transaksinya benar-benar pendek.
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
