import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import USER_ROLE, Base


class User(Base):
    """Akun login. Hanya data akun, tanpa data klinis."""

    __tablename__ = "users"
    __table_args__ = (
        Index("users_username_uq", text("lower(username)"), unique=True),
        CheckConstraint("char_length(username) BETWEEN 3 AND 50", name="users_username_len"),
        CheckConstraint(
            r"nomor_wa IS NULL OR nomor_wa ~ '^(\+62|62|0)8[0-9]{8,12}$'",
            name="users_wa_format",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    username: Mapped[str] = mapped_column(Text, nullable=False)
    # Hash argon2 (pwdlib). Tidak pernah plaintext.
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        USER_ROLE, nullable=False, server_default=text("'pasien'")
    )
    nama_lengkap: Mapped[str] = mapped_column(Text)
    nomor_wa: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )