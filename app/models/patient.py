import uuid
from datetime import date, datetime

from sqlalchemy import (
    CHAR,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GENDER, Base


class Patient(Base):
    """Identitas klinis pasien (ibu atau bayi). Satu akun bisa punya banyak pasien.

    user_id nullable mempertahankan desain skema; pada praktiknya (tanpa walk-in)
    selalu terisi, dan merge pasien dipindahkan via merged_into_id.
    """

    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("no_rm", name="patients_no_rm_uq"),
        # NIK bayi sering belum ada; unik hanya bila terisi
        Index("patients_nik_uq", "nik", unique=True, postgresql_where=text("nik IS NOT NULL")),
        Index("patients_user_idx", "user_id"),
        CheckConstraint(r"nik IS NULL OR nik ~ '^[0-9]{16}$'", name="patients_nik_fmt"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    # RM-000001 dst, otomatis dari sequence. Tidak diubah, tidak dipakai ulang.
    no_rm: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'RM-' || lpad(nextval('patient_rm_seq')::text, 6, '0')"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    nik: Mapped[str | None] = mapped_column(CHAR(16))
    nama_lengkap: Mapped[str] = mapped_column(Text, nullable=False)
    tanggal_lahir: Mapped[date] = mapped_column(Date, nullable=False)
    jenis_kelamin: Mapped[str] = mapped_column(GENDER, nullable=False)
    nama_penanggung_jawab: Mapped[str | None] = mapped_column(Text)
    nomor_wa: Mapped[str | None] = mapped_column(Text)
    alamat: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("patients.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
