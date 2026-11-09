"""Shared fixtures untuk test API (httpx + ASGI transport, tanpa server hidup)."""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest

from app.db import dispose_engine
from app.main import app


@pytest.fixture(autouse=True)
async def fresh_engine() -> AsyncIterator[None]:
    """Engine global dibuat per satu event loop; pytest-asyncio membuat loop baru
    per test. Buang engine tiap test agar pool tidak terikat ke loop yang salah."""
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c


@pytest.fixture
def unique_username() -> str:
    """Username unik per test agar tidak berbenturan antar test dan run berulang."""
    return f"t_{uuid.uuid4().hex[:12]}"
