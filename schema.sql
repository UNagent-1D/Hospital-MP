CREATE TABLE IF NOT EXISTS doctors (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL,
    area  TEXT NOT NULL,
    phone TEXT NOT NULL,
    place TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appointments (
    id            TEXT PRIMARY KEY,
    doctor_id     TEXT NOT NULL REFERENCES doctors(id),
    doctor_name   TEXT NOT NULL,
    patient_ref   TEXT NOT NULL,
    patient_name  TEXT NOT NULL,
    specialty     TEXT NOT NULL,
    slot_start    TEXT NOT NULL,
    slot_end      TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
    created_at    TEXT NOT NULL,
    cancelled_at  TEXT,
    cancel_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_appts_doctor_id   ON appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_appts_patient_ref ON appointments(patient_ref);
