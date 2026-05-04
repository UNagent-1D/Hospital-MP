"""Run once to populate the Supabase database with initial data: python seed.py"""
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

DOCTORS = [
    {"id": "doc-001", "name": "Dr. Alejandra Rios",  "area": "Cardiologist",        "phone": "+573101234567", "place": "Bogota Norte — Clínica San Ignacio, Room 4A"},
    {"id": "doc-002", "name": "Dr. Carlos Mendoza",  "area": "Pediatrician",         "phone": "+573107654321", "place": "Bogota Sur — Torre Médica Central, Floor 2"},
    {"id": "doc-003", "name": "Dr. Laura Estrada",   "area": "General Practitioner", "phone": "+573109876543", "place": "Medellin Centro — Centro Médico Poblado, Room 101"},
    {"id": "doc-004", "name": "Dr. Marcos Villegas", "area": "Neurologist",          "phone": "+573102345678", "place": "Bogota Norte — Clínica San Ignacio, Neurology Wing, Room 7"},
    {"id": "doc-005", "name": "Dr. Sofia Herrera",   "area": "Pediatrician",         "phone": "+573108765432", "place": "Bogota Sur — Hospital El Tunal, Pediatrics Block B"},
]

sb.table("doctors").upsert(DOCTORS).execute()
print(f"Seeded {len(DOCTORS)} doctors.")

existing = sb.table("appointments").select("id", count="exact").execute()
if existing.count == 0:
    now_iso = datetime.now(timezone.utc).isoformat()
    APPOINTMENTS = [
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
    sb.table("appointments").insert(APPOINTMENTS).execute()
    print(f"Seeded {len(APPOINTMENTS)} appointments.")
else:
    print("Appointments table not empty, skipping seed.")
