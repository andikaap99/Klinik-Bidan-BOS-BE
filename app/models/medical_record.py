import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MedicalRecord(Base):
    """Rekam medis SOAP, 1:1 dengan kunjungan.

    Insert-only di level API (sekali simpan, tanpa PUT/PATCH). ON DELETE RESTRICT
    agar tidak ikut terhapus bersama kunjungan/pasien.
    """

    __tablename__ = "medical_records"
    __table_args__ = (
        UniqueConstraint("visit_id", name="medical_records_visit_id_uq"),
        Index(
            "mr_next_control_idx",
            "next_control_date",
            postgresql_where=text("next_control_date IS NOT NULL"),
        ),
        CheckConstraint("jsonb_typeof(objective) = 'object'", name="mr_objective_obj"),
        CheckConstraint("jsonb_typeof(service_details) = 'object'", name="mr_details_obj"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False
    )
    # Role bidan divalidasi di aplikasi, bukan di database
    examined_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id")
    )
    # S: keluhan utama yang terverifikasi bidan (kunjungan keluhan pasien)
    subjective: Mapped[str | None] = mapped_column(Text)
    # O: tekanan darah, BB, TB, suhu, DJJ, TFU, dll — objek fleksibel
    objective: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )
    assessment: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[str | None] = mapped_column(Text)
    # Catatan khusus per layanan (HPHT, usia kehamilan, vaksin, dll.)
    service_details: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )
    # "Feedback" yang tampil ke pasien versinya sendiri
    patient_note: Mapped[str | None] = mapped_column(Text)
    next_control_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
