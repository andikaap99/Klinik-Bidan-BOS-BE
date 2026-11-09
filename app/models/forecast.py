from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Forecast(Base):
    """Hasil prediksi kedatangan harian per layanan, hasil cron forecast job."""

    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint("generated_at", "target_date", "service_id", name="forecasts_uq"),
        Index("forecasts_date_idx", "target_date"),
        CheckConstraint("predicted_count >= 0", name="forecasts_count_positive"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    predicted_count: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    # generated_at membedakan satu eksekusi job dari eksekusi lain
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
