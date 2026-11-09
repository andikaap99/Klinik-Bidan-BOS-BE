"""Model ORM. Semua model WAJIB di-import di sini agar terdaftar di Base.metadata
(dipakai alembic autogenerate dan query aplikasi)."""

from app.models.base import Base
from app.models.clinic_closure import ClinicClosure
from app.models.forecast import Forecast
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.queue_counter import QueueCounter
from app.models.service import Service
from app.models.user import User
from app.models.visit import Visit

__all__ = [
    "Base",
    "ClinicClosure",
    "Forecast",
    "MedicalRecord",
    "Patient",
    "QueueCounter",
    "Service",
    "User",
    "Visit",
]
