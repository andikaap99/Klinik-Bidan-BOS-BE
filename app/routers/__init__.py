"""Aggregator seluruh router yang dipasang di bawah /api/v1 (kontrak API 2026-11-07)."""

from fastapi import APIRouter

from app.routers import health

api_router = APIRouter()
api_router.include_router(health.router)
