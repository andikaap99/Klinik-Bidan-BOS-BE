"""Tests CORS (keputusan sisi server: origin dari .env, tanpa credentials cookie).

CORS hanya relevan untuk browser; curl/Postman tidak terpengaruh. Test ini
mengunci perilaku middleware agar tidak regresi saat FE/origin berubah.
"""

import pytest

from app.core.config import get_settings

pytestmark = pytest.mark.asyncio

_ALLOWED_ORIGINS = get_settings().cors_origin_list
# origin dev pertama di .env.example (localhost:5173)
_LOCAL = _ALLOWED_ORIGINS[0]


async def test_preflight_allowed_origin(client) -> None:
    res = await client.options(
        "/login",
        headers={
            "Origin": _LOCAL,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == _LOCAL
    assert "POST" in res.headers["access-control-allow-methods"]
    assert "content-type" in res.headers["access-control-allow-headers"].lower()


async def test_preflight_tunnel_origin_allowed(client) -> None:
    """Origin cloudflared tunnel (bidan.delta-zero.my.id) harus diizinkan."""
    tunnel = next(o for o in _ALLOWED_ORIGINS if "delta-zero.my.id" in o)
    res = await client.options(
        "/login",
        headers={
            "Origin": tunnel,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == tunnel


async def test_disallowed_origin_gets_no_acao_header(client) -> None:
    res = await client.options(
        "/login",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in res.headers


async def test_actual_request_has_acao_header(client) -> None:
    """Request biasa juga wajib punya ACAO (tidak hanya preflight)."""
    res = await client.post(
        "/login", json={"username": "nonexistent_user", "password": "salah12345"},
        headers={"Origin": _LOCAL},
    )
    assert res.status_code == 401
    assert res.headers["access-control-allow-origin"] == _LOCAL
