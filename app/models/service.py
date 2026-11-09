from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Identity,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Service(Base):
    """Master layanan + durasi stagis untuk estimasi tunggu (bukan hasil model)."""

    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("kode", name="services_kode_uq"),
        CheckConstraint("avg_duration_minutes > 0", name="services_duration_positive"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    kode: Mapped[str] = mapped_column(Text, nullable=False)
    nama: Mapped[str] = mapped_column(Text, nullable=False)
    # Seed layanan sengaja kosong (keputusan: "let it be empty for now")
    avg_duration_minutes: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("15")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
