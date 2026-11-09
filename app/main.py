"""Entry point FastAPI.

Semua path di bawah /api/v1 (kontrak). Swagger UI: /api/v1/docs.
Cron job forecast dipasang terpisah (host cron), tidak di sini.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.db import dispose_engine
from app.routers import api_router

logger = logging.getLogger(__name__)

_JWT_SECRET_DEFAULT = "dev-secret-ganti-di-env"


def _validate_prod_settings() -> None:
    """Cegah deployment prod dengan secret bawaan / kelemahan konfigurasi."""
    settings = get_settings()
    if settings.app_env != "prod":
        return
    if settings.jwt_secret == _JWT_SECRET_DEFAULT:
        raise RuntimeError(
            "JWT_SECRET masih memakai nilai bawaan dev; wajib diganti di .env sebelum prod."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_prod_settings()
    logger.info("Aplikasi siap (env=%s)", get_settings().app_env)
    yield
    await dispose_engine()


app = FastAPI(
    title="DSS Klinik Bersalin (BidanCare)",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)

# CORS: origin diambil dari CORS_ORIGINS (.env, dipisah koma).
# allow_credentials=False karena JWT dikirim via header Authorization, bukan cookie.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
