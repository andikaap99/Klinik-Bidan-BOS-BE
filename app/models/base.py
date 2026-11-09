"""Base declarative + konvensi penamaan constraint + tipe enum native PostgreSQL.

Nama enum HARUS sama dengan schema_v1.sql: user_role, gender, visit_status, visit_session.
"""

from sqlalchemy import Enum as SAEnum
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Satu instance tipe per enum agar dibuat sekali dan dipakai berbagi antar tabel.
USER_ROLE = SAEnum("pasien", "bidan", "admin", name="user_role", native_enum=True)
GENDER = SAEnum("L", "P", name="gender", native_enum=True)
VISIT_STATUS = SAEnum(
    "antre", "diperiksa", "selesai", "batal", name="visit_status", native_enum=True
)
VISIT_SESSION = SAEnum("pagi_siang", "sore_malam", name="visit_session", native_enum=True)
