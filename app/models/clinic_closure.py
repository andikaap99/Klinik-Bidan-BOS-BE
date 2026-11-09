from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Identity,
    Index,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import VISIT_SESSION, Base


class ClinicClosure(Base):
    """Hari tutup / bidan absen (Open Decision #2, baseline schema_v1).

    sesi NULL = tutup seharian. Membedakan hari tutup dari hari sepi saat
    training prediksi, dan memblokir pendaftaran di hari tutup.
    """

    __tablename__ = "clinic_closures"
    __table_args__ = (
        Index(
            "clinic_closures_day_uq",
            "tanggal",
            unique=True,
            postgresql_where=text("sesi IS NULL"),
        ),
        Index(
            "clinic_closures_sesi_uq",
            "tanggal",
            "sesi",
            unique=True,
            postgresql_where=text("sesi IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tanggal: Mapped[date] = mapped_column(Date, nullable=False)
    sesi: Mapped[str | None] = mapped_column(VISIT_SESSION)
    alasan: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
