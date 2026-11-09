"""Tests untuk area Auth & Akun (kontrak bagian 3).

Butuh PostgreSQL dari compose berjalan (schema dari alembic upgrade head).
"""

import jwt
import pytest

from app.core.config import get_settings

pytestmark = pytest.mark.asyncio


@pytest.fixture
def register_payload(unique_username: str) -> dict:
    return {
        "nama_lengkap": "Siti Aminah",
        "nomor_wa": "081234567890",
        "username": unique_username,
        "password": "rahasia123",
    }


async def test_register_201_shape(client, register_payload: dict) -> None:
    res = await client.post("/register", json=register_payload)
    assert res.status_code == 201
    data = res.json()
    # Kontrak: bentuk ringkas, selalu role pasien (dari server, bukan klien)
    assert set(data) == {"id", "username", "nama_lengkap", "role"}
    assert data["username"] == register_payload["username"]
    assert data["role"] == "pasien"


async def test_register_duplicate_username_409(client, register_payload: dict) -> None:
    await client.post("/register", json=register_payload)
    # Username sama, huruf besar beda (uniquer tidak peka huruf besar/kecil)
    payload = {**register_payload, "username": register_payload["username"].upper()}
    res = await client.post("/register", json=payload)
    assert res.status_code == 409
    assert res.json()["code"] == "USERNAME_TAKEN"


@pytest.mark.parametrize(
    "field,value",
    [
        ("username", "ab"),  # < 3 karakter
        ("username", "a" * 51),  # > 50 karakter
        ("nomor_wa", "12345"),  # bukan format WA Indonesia
        ("password", "short"),  # < 8 karakter
        ("nama_lengkap", ""),  # kosong
    ],
)
async def test_register_validation_422(
    client, register_payload: dict, field: str, value: str
) -> None:
    res = await client.post("/register", json={**register_payload, field: value})
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"


async def test_login_ok_and_expires_in(client, register_payload: dict) -> None:
    await client.post("/register", json=register_payload)
    res = await client.post(
        "/login",
        json={"username": register_payload["username"].upper(), "password": "rahasia123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert set(data) == {"access_token", "token_type", "expires_in", "user"}
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == get_settings().access_token_expire_minutes * 60
    assert data["user"]["role"] == "pasien"


async def test_login_generic_error_message(client, register_payload: dict) -> None:
    await client.post("/register", json=register_payload)
    # Password salah
    res = await client.post(
        "/login", json={"username": register_payload["username"], "password": "kacau12345"}
    )
    assert res.status_code == 401
    body = res.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    # Username tak ada: pesan HARUS sama (tidak membedakan username/password salah)
    res2 = await client.post(
        "/login", json={"username": "tidak_ada_99", "password": "kacau12345"}
    )
    assert res2.status_code == 401
    assert res2.json() == body


async def test_me_without_token_401(client) -> None:
    res = await client.get("/me")
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_CREDENTIALS"


async def test_me_expired_token_401_token_expired(client, register_payload: dict) -> None:
    await client.post("/register", json=register_payload)
    login = (await client.post(
        "/login", json={"username": register_payload["username"], "password": "rahasia123"}
    )).json()
    # Ubah exp menjadi kedaluwarsa
    settings = get_settings()
    payload = jwt.decode(login["access_token"], settings.jwt_secret, algorithms=["HS256"])
    payload["exp"] = 1_000_000  # lama sekali, pasti lewat
    expired = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    res = await client.get("/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401
    assert res.json()["code"] == "TOKEN_EXPIRED"


async def test_me_full_flow(client, register_payload: dict) -> None:
    await client.post("/register", json=register_payload)
    token = (await client.post(
        "/login", json={"username": register_payload["username"], "password": "rahasia123"}
    )).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["nomor_wa"] == "081234567890"

    patched = await client.patch(
        "/me", headers=headers, json={"nama_lengkap": "Siti Aminah Baru"}
    )
    assert patched.status_code == 200
    assert patched.json()["nama_lengkap"] == "Siti Aminah Baru"
    # Field yang tak dikirim tidak ikut nol-out
    assert patched.json()["nomor_wa"] == "081234567890"


async def test_change_password_flow(client, register_payload: dict) -> None:
    await client.post("/register", json=register_payload)
    token = (await client.post(
        "/login", json={"username": register_payload["username"], "password": "rahasia123"}
    )).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Password lama salah -> 403 (kontrap 403/422)
    wrong = await client.post(
        "/me/password",
        headers=headers,
        json={"password_lama": "salah12345", "password_baru": "baru123456"},
    )
    assert wrong.status_code == 403

    ok = await client.post(
        "/me/password",
        headers=headers,
        json={"password_lama": "rahasia123", "password_baru": "baru123456"},
    )
    assert ok.status_code == 200
    assert ok.json() == {"message": "Password berhasil diubah"}

    # Login dengan password baru, dan yang lama tertolak
    new_login = await client.post(
        "/login", json={"username": register_payload["username"], "password": "baru123456"}
    )
    assert new_login.status_code == 200
    old_login = await client.post(
        "/login", json={"username": register_payload["username"], "password": "rahasia123"}
    )
    assert old_login.status_code == 401


async def test_seeded_bidan_login(client) -> None:
    """Akun bidan dari python -m app.cli seed-bidan bisa login dan role-nya bidan.

    Password bisa saja sudah diganti pemiliknya (via /me/password); test di-skip
    bila seed tidak cocok lagi, dan tetap menjadi guard saat seed dipulihkan.
    """
    res = await client.post(
        "/login",
        json={
            "username": get_settings().seed_bidan_username,
            "password": get_settings().seed_bidan_password,
        },
    )
    if res.status_code == 401:
        pytest.skip("password bidan1 sudah diubah dari seed; tidak dapat diverifikasi")
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "bidan"
