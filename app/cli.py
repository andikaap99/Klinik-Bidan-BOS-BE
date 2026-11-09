"""CLI aplikasi: seeding akun & utilities dev.

Pemakaian:
    uv run python -m app.cli seed-bidan
"""

import argparse
import asyncio
import sys

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db import get_session_factory
from app.models import User


async def seed_bidan() -> int:
    """Buat akun bidan default (idempoten) dari SEED_BIDAN_* di settings."""
    settings = get_settings()
    username = settings.seed_bidan_username
    if not username or not settings.seed_bidan_password:
        print("SEED_BIDAN_USERNAME / SEED_BIDAN_PASSWORD tidak lengkap di .env", file=sys.stderr)
        return 2

    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            existing = await session.scalar(
                select(User).where(func.lower(User.username) == username.lower())
            )
            if existing is not None:
                print(
                    f"Akun bidan '{existing.username}' (id={existing.id}) sudah ada; skip."
                )
                return 0
            user = User(
                username=username,
                password_hash=hash_password(settings.seed_bidan_password),
                role="bidan",
                nama_lengkap=settings.seed_bidan_nama_lengkap or username,
            )
            session.add(user)
    print(f"Akun bidan '{username}' dibuat (id={user.id}).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="Utilities CLI aplikasi")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed-bidan", help="Buat akun bidan default (idempoten)")

    args = parser.parse_args(argv)

    if args.command == "seed-bidan":
        return asyncio.run(seed_bidan())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
