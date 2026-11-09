-- =====================================================================
-- Skema PostgreSQL: DSS Klinik Bersalin (baseline v1)
-- Target: PostgreSQL 14+
-- Termasuk: clinic_closures dan v_daily_visits_filled
-- Belum termasuk: layanan PERSALINAN (menunggu keputusan PM)
-- =====================================================================
BEGIN;

-- ---------- Enum ----------
CREATE TYPE user_role     AS ENUM ('pasien', 'bidan', 'admin');
CREATE TYPE gender        AS ENUM ('L', 'P');
CREATE TYPE visit_status  AS ENUM ('antre', 'diperiksa', 'selesai', 'batal');
CREATE TYPE visit_session AS ENUM ('pagi_siang', 'sore_malam');

-- ---------- Trigger updated_at ----------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END $$;

-- =====================================================================
-- users
-- =====================================================================
CREATE TABLE users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username      text        NOT NULL,
  password_hash text        NOT NULL,
  role          user_role   NOT NULL DEFAULT 'pasien',
  nama_lengkap  text        NOT NULL,
  nomor_wa      text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT users_username_len CHECK (char_length(username) BETWEEN 3 AND 50),
  CONSTRAINT users_wa_format    CHECK (nomor_wa IS NULL
                                       OR nomor_wa ~ '^(\+62|62|0)8[0-9]{8,12}$')
);
CREATE UNIQUE INDEX users_username_uq ON users (lower(username));
CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =====================================================================
-- patients
-- =====================================================================
CREATE SEQUENCE patient_rm_seq;

CREATE TABLE patients (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  no_rm                 text NOT NULL
                        DEFAULT 'RM-' || lpad(nextval('patient_rm_seq')::text, 6, '0'),
  user_id               uuid REFERENCES users(id) ON DELETE SET NULL,
  nik                   char(16),
  nama_lengkap          text   NOT NULL,
  tanggal_lahir         date   NOT NULL,
  jenis_kelamin         gender NOT NULL,
  nama_penanggung_jawab text,
  nomor_wa              text,
  alamat                text,
  deleted_at            timestamptz,
  merged_into_id        uuid REFERENCES patients(id),
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT patients_no_rm_uq UNIQUE (no_rm),
  CONSTRAINT patients_nik_fmt  CHECK (nik IS NULL OR nik ~ '^[0-9]{16}$')
);
CREATE UNIQUE INDEX patients_nik_uq   ON patients (nik) WHERE nik IS NOT NULL;
CREATE INDEX        patients_user_idx ON patients (user_id);
CREATE TRIGGER trg_patients_updated BEFORE UPDATE ON patients
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =====================================================================
-- services
-- =====================================================================
CREATE TABLE services (
  id                   smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  kode                 text     NOT NULL UNIQUE,
  nama                 text     NOT NULL,
  avg_duration_minutes smallint NOT NULL DEFAULT 15 CHECK (avg_duration_minutes > 0),
  created_at           timestamptz NOT NULL DEFAULT now()
);

-- =====================================================================
-- queue_counters
-- =====================================================================
CREATE TABLE queue_counters (
  visit_date  date          NOT NULL,
  sesi        visit_session NOT NULL,
  last_number integer       NOT NULL,
  PRIMARY KEY (visit_date, sesi)
);

-- Panggil di dalam transaksi yang sama dengan INSERT visits
CREATE OR REPLACE FUNCTION next_queue_number(p_date date, p_sesi visit_session)
RETURNS integer LANGUAGE sql AS $$
  INSERT INTO queue_counters (visit_date, sesi, last_number)
  VALUES (p_date, p_sesi, 1)
  ON CONFLICT (visit_date, sesi)
  DO UPDATE SET last_number = queue_counters.last_number + 1
  RETURNING last_number;
$$;

-- =====================================================================
-- visits
-- =====================================================================
CREATE TABLE visits (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id    uuid          NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
  service_id    smallint      NOT NULL REFERENCES services(id),
  visit_date    date          NOT NULL,
  sesi          visit_session NOT NULL,
  queue_number  integer       NOT NULL CHECK (queue_number > 0),
  status        visit_status  NOT NULL DEFAULT 'antre',
  keluhan       text,
  registered_by uuid REFERENCES users(id),
  registered_at timestamptz   NOT NULL DEFAULT now(),
  started_at    timestamptz,
  finished_at   timestamptz,
  created_at    timestamptz   NOT NULL DEFAULT now(),
  updated_at    timestamptz   NOT NULL DEFAULT now(),
  CONSTRAINT visits_queue_uq   UNIQUE (visit_date, sesi, queue_number),
  CONSTRAINT visits_time_order CHECK (finished_at IS NULL OR started_at IS NULL
                                      OR finished_at >= started_at)
);
CREATE UNIQUE INDEX visits_no_dup_active_uq
  ON visits (patient_id, visit_date, service_id) WHERE status <> 'batal';
CREATE INDEX visits_patient_hist_idx ON visits (patient_id, visit_date DESC);
CREATE INDEX visits_date_service_idx ON visits (visit_date, service_id);
CREATE INDEX visits_active_queue_idx ON visits (visit_date, sesi, queue_number)
  WHERE status IN ('antre', 'diperiksa');
CREATE TRIGGER trg_visits_updated BEFORE UPDATE ON visits
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =====================================================================
-- medical_records
-- =====================================================================
CREATE TABLE medical_records (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  visit_id          uuid  NOT NULL UNIQUE REFERENCES visits(id) ON DELETE RESTRICT,
  examined_by       uuid  REFERENCES users(id),
  subjective        text,
  objective         jsonb NOT NULL DEFAULT '{}',
  assessment        text,
  plan              text,
  service_details   jsonb NOT NULL DEFAULT '{}',
  patient_note      text,
  next_control_date date,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT mr_objective_obj CHECK (jsonb_typeof(objective) = 'object'),
  CONSTRAINT mr_details_obj   CHECK (jsonb_typeof(service_details) = 'object')
);
CREATE INDEX mr_next_control_idx ON medical_records (next_control_date)
  WHERE next_control_date IS NOT NULL;
CREATE TRIGGER trg_mr_updated BEFORE UPDATE ON medical_records
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =====================================================================
-- forecasts
-- =====================================================================
CREATE TABLE forecasts (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  target_date     date     NOT NULL,
  service_id      smallint NOT NULL REFERENCES services(id),
  predicted_count numeric(8,2) NOT NULL CHECK (predicted_count >= 0),
  generated_at    timestamptz  NOT NULL DEFAULT now(),
  CONSTRAINT forecasts_uq UNIQUE (generated_at, target_date, service_id)
);
CREATE INDEX forecasts_date_idx ON forecasts (target_date);

-- =====================================================================
-- clinic_closures (hari / sesi tutup)
-- =====================================================================
CREATE TABLE clinic_closures (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tanggal    date NOT NULL,
  sesi       visit_session,            -- NULL = tutup seharian
  alasan     text,                     -- libur nasional, bidan absen, dll
  created_at timestamptz NOT NULL DEFAULT now()
);
-- UNIQUE biasa tidak menangkap NULL, jadi dipisah dua index parsial
CREATE UNIQUE INDEX clinic_closures_day_uq
  ON clinic_closures (tanggal) WHERE sesi IS NULL;
CREATE UNIQUE INDEX clinic_closures_sesi_uq
  ON clinic_closures (tanggal, sesi) WHERE sesi IS NOT NULL;

-- =====================================================================
-- Views
-- =====================================================================
-- Hanya memuat hari yang punya kunjungan
CREATE VIEW v_daily_visits AS
SELECT visit_date, sesi, service_id, count(*)::int AS total
FROM visits
WHERE status <> 'batal'
GROUP BY visit_date, sesi, service_id;

-- Untuk data training: hari buka tanpa kunjungan diisi 0 (per layanan),
-- hari tutup seharian dibuang. Total per hari per layanan (semua sesi digabung).
CREATE VIEW v_daily_visits_filled AS
SELECT d::date AS visit_date, s.id AS service_id, COALESCE(v.total, 0) AS total
FROM generate_series((SELECT min(visit_date) FROM visits)::timestamp,
                     current_date::timestamp, interval '1 day') d
CROSS JOIN services s
LEFT JOIN (SELECT visit_date, service_id, count(*)::int AS total
             FROM visits WHERE status <> 'batal'
            GROUP BY visit_date, service_id) v
       ON v.visit_date = d::date AND v.service_id = s.id
WHERE NOT EXISTS (SELECT 1 FROM clinic_closures c
                   WHERE c.tanggal = d::date AND c.sesi IS NULL);

-- Posisi antrian + estimasi waktu tunggu (menit), dihitung per tanggal dan sesi
CREATE VIEW v_queue_estimation AS
SELECT
  v.id AS visit_id,
  v.visit_date,
  v.sesi,
  v.queue_number,
  v.status,
  (SELECT count(*)
     FROM visits a
    WHERE a.visit_date = v.visit_date
      AND a.sesi = v.sesi
      AND a.status IN ('antre', 'diperiksa')
      AND a.queue_number < v.queue_number)                    AS antrean_di_depan,
  COALESCE((SELECT sum(s.avg_duration_minutes)
              FROM visits a
              JOIN services s ON s.id = a.service_id
             WHERE a.visit_date = v.visit_date
               AND a.sesi = v.sesi
               AND a.status IN ('antre', 'diperiksa')
               AND a.queue_number < v.queue_number), 0)::int  AS estimasi_menit
FROM visits v
WHERE v.status IN ('antre', 'diperiksa');

-- Prediksi dari eksekusi terbaru
CREATE VIEW v_latest_forecast AS
SELECT target_date, service_id, predicted_count, generated_at
FROM forecasts
WHERE generated_at = (SELECT max(generated_at) FROM forecasts);

COMMIT;

-- =====================================================================
-- Contoh pemakaian (jangan dijalankan sebagai bagian migrasi)
-- =====================================================================
-- Daftar kunjungan (satu transaksi pendek):
-- BEGIN;
-- INSERT INTO visits (patient_id, service_id, visit_date, sesi, queue_number, keluhan, registered_by)
-- VALUES ('<patient_uuid>', 1, CURRENT_DATE, 'pagi_siang',
--         next_queue_number(CURRENT_DATE, 'pagi_siang'), 'Kontrol kehamilan', '<user_uuid>')
-- RETURNING id, queue_number;
-- COMMIT;
--
-- Cek apakah tanggal dan sesi tutup (validasi pendaftaran):
-- SELECT EXISTS (SELECT 1 FROM clinic_closures
--                 WHERE tanggal = $1 AND (sesi IS NULL OR sesi = $2)) AS tutup;
--
-- Pengaman transaksi yang disarankan:
-- ALTER DATABASE nama_db SET lock_timeout = '5s';
-- ALTER DATABASE nama_db SET idle_in_transaction_session_timeout = '10s';
