import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import VISIT_SESSION, VISIT_STATUS, Base


class Visit(Base):
    """Satu kali kedatangan; merangkap pendaftaran dan antrian.

    Nomor antrian ditentukan saat submit via next_queue_number() di transaksi
    yang sama (pendek). Nomor dari kunjungan batal tidak dipakai ulang.
    """

    __tablename__ = "visits"
    __table_args__ = (
        UniqueConstraint("visit_date", "sesi", "queue_number", name="visits_queue_uq"),
        # Cegah daftar ganda layanan sama di hari sama (kecuali batal)
        Index(
            "visits_no_dup_active_uq",
            "patient_id",
            "visit_date",
            "service_id",
            unique=True,
            postgresql_where=text("status <> 'batal'"),
        ),
        Index("visits_patient_hist_idx", "patient_id", text("visit_date DESC")),
        Index("visits_date_service_idx", "visit_date", "service_id"),
        Index(
            "visits_active_queue_idx",
            "visit_date",
            "sesi",
            "queue_number",
            postgresql_where=text("status IN ('antre', 'diperiksa')"),
        ),
        CheckConstraint("queue_number > 0", name="visits_queue_positive"),
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name="visits_time_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id"), nullable=False
    )
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    sesi: Mapped[str] = mapped_column(VISIT_SESSION, nullable=False)
    queue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(VISIT_STATUS, nullable=False)
    # Keluhan versi pasien saat mendaftar (beda arti dengan medical_records.subjective)
    keluhan: Mapped[str | None] = mapped_column(Text)
    registered_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id")
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
