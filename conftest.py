import copy
import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from app import app as flask_app
from fake_db import FakeSupabaseClient

SEED_DOCTORS = [
    {"id": "doc-001", "name": "Dr. Alejandra Rios",  "area": "Cardiologist",        "phone": "+573101234567", "place": "Bogota Norte — Clínica San Ignacio, Room 4A"},
    {"id": "doc-002", "name": "Dr. Carlos Mendoza",  "area": "Pediatrician",         "phone": "+573107654321", "place": "Bogota Sur — Torre Médica Central, Floor 2"},
    {"id": "doc-003", "name": "Dr. Laura Estrada",   "area": "General Practitioner", "phone": "+573109876543", "place": "Medellin Centro — Centro Médico Poblado, Room 101"},
    {"id": "doc-004", "name": "Dr. Marcos Villegas", "area": "Neurologist",          "phone": "+573102345678", "place": "Bogota Norte — Clínica San Ignacio, Neurology Wing, Room 7"},
    {"id": "doc-005", "name": "Dr. Sofia Herrera",   "area": "Pediatrician",         "phone": "+573108765432", "place": "Bogota Sur — Hospital El Tunal, Pediatrics Block B"},
]


def _seed_appointments() -> list:
    now_iso = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": "appt-seed-001",
            "doctor_id": "doc-001", "doctor_name": "Dr. Alejandra Rios",
            "patient_ref": "HOSP-PAT-00492", "patient_name": "Maria Gomez Torres",
            "specialty": "Cardiologist",
            "slot_start": "2026-03-15T09:00:00", "slot_end": "2026-03-15T09:30:00",
            "status": "confirmed", "created_at": now_iso,
            "cancelled_at": None, "cancel_reason": None,
        },
        {
            "id": "appt-seed-002",
            "doctor_id": "doc-003", "doctor_name": "Dr. Laura Estrada",
            "patient_ref": "HOSP-PAT-00492", "patient_name": "Maria Gomez Torres",
            "specialty": "General Practitioner",
            "slot_start": "2026-03-20T11:00:00", "slot_end": "2026-03-20T11:30:00",
            "status": "confirmed", "created_at": now_iso,
            "cancelled_at": None, "cancel_reason": None,
        },
    ]


@pytest.fixture(autouse=True)
def fake_db():
    """Reset to clean seed state before every test."""
    fake = FakeSupabaseClient(
        doctors=copy.deepcopy(SEED_DOCTORS),
        appointments=_seed_appointments(),
    )
    with patch("app.get_db", return_value=fake):
        yield fake


@pytest.fixture
def client(fake_db):
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c
