"""master layanan v1 (seed 8 layanan, CHECK durasi >= 0)

Revision ID: dfc4c98955cf
Revises: c5d6845bba31
Create Date: 2026-11-14

Master layanan dari Jira (2026-11-14):
- 8 layanan, urutan menentukan id pada DB baru.
- Ibu Bersalin durasi 0 (belum tentu); karena itu CHECK diperlonggar
  dari `> 0` menjadi `>= 0`. Kolom tetap NOT NULL.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dfc4c98955cf"
down_revision: str = "c5d6845bba31"
branch_labels: str | None = None
depends_on: str | None = None

# (kode, nama, avg_duration_minutes) — urutan sesuai Jira
_SEED = [
    ("IBU_HAMIL", "Pemeriksaan Ibu Hamil", 60),
    ("IBU_BERSALIN", "Ibu Bersalin", 0),  # durasi belum tentu; 0 sengaja
    ("IMUNISASI", "Imunisasi", 15),
    ("KB", "Pelayanan KB", 30),
    ("BEROBAT", "Berobat", 45),
    ("PIJAT_BAYI", "Pijat Bayi", 60),
    ("USG", "Pemeriksaan USG", 45),
    ("PROGRAM_KEHAMILAN", "Program Kehamilan", 45),
]


def upgrade() -> None:
    # Durasi 0 (Ibu Bersalin) melanggar CHECK lama; perlonggar dulu.
    # Pakai SQL mentah: op.drop_constraint akan menerapkan naming_convention
    # env.py dan menghasilkan nama double-prefix.
    op.execute("ALTER TABLE services DROP CONSTRAINT ck_services_services_duration_positive")
    op.execute("ALTER TABLE services ADD CONSTRAINT ck_services_services_duration_positive "
               "CHECK (avg_duration_minutes >= 0)")
    op.bulk_insert(
        sa.table(
            "services",
            sa.column("kode", sa.Text),
            sa.column("nama", sa.Text),
            sa.column("avg_duration_minutes", sa.SmallInteger),
        ),
        [
            {"kode": kode, "nama": nama, "avg_duration_minutes": durasi}
            for kode, nama, durasi in _SEED
        ],
    )


def downgrade() -> None:
    # Hapus baris seed dulu agar tidak melanggar CHECK > 0 yang dikembalikan
    for kode, _, _ in _SEED:
        op.execute(sa.text("DELETE FROM services WHERE kode = :kode").bindparams(kode=kode))
    op.execute("ALTER TABLE services DROP CONSTRAINT ck_services_services_duration_positive")
    op.execute("ALTER TABLE services ADD CONSTRAINT ck_services_services_duration_positive "
               "CHECK (avg_duration_minutes > 0)")
