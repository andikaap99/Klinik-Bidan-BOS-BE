from datetime import date

from sqlalchemy import Date, Integer, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import VISIT_SESSION, Base


class QueueCounter(Base):
    """Counter nomor antrian atomik per (tanggal, sesi).

    Tanpa FK ke tabel lain; terhubung secara logika lewat (visit_date, sesi).
    Dikunci UPDATE ON CONFLICT oleh next_queue_number() di dalam transaksi insert.
    """

    __tablename__ = "queue_counters"
    __table_args__ = (PrimaryKeyConstraint("visit_date", "sesi"),)

    visit_date: Mapped[date] = mapped_column(Date, primary_key=True)
    sesi: Mapped[str] = mapped_column(VISIT_SESSION, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False)
