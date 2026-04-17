import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

DOCTORS = {
    "doc-001": {
        "id": "doc-001",
        "name": "Dr. Alejandra Rios",
        "area": "Cardiologist",
        "phone": "+573101234567",
        "place": "Bogota Norte — Clínica San Ignacio, Room 4A",
    },
    "doc-002": {
        "id": "doc-002",
        "name": "Dr. Carlos Mendoza",
        "area": "Pediatrician",
        "phone": "+573107654321",
        "place": "Bogota Sur — Torre Médica Central, Floor 2",
    },
    "doc-003": {
        "id": "doc-003",
        "name": "Dr. Laura Estrada",
        "area": "General Practitioner",
        "phone": "+573109876543",
        "place": "Medellin Centro — Centro Médico Poblado, Room 101",
    },
    "doc-004": {
        "id": "doc-004",
        "name": "Dr. Marcos Villegas",
        "area": "Neurologist",
        "phone": "+573102345678",
        "place": "Bogota Norte — Clínica San Ignacio, Neurology Wing, Room 7",
    },
    "doc-005": {
        "id": "doc-005",
        "name": "Dr. Sofia Herrera",
        "area": "Pediatrician",
        "phone": "+573108765432",
        "place": "Bogota Sur — Hospital El Tunal, Pediatrics Block B",
    },
}

now_iso = datetime.now(timezone.utc).isoformat()

APPOINTMENTS = {
    "appt-seed-001": {
        "id": "appt-seed-001",
        "doctor_id": "doc-001",
        "doctor_name": "Dr. Alejandra Rios",
        "patient_ref": "HOSP-PAT-00492",
        "patient_name": "Maria Gomez Torres",
        "specialty": "Cardiologist",
        "slot_start": "2026-03-15T09:00:00",
        "slot_end": "2026-03-15T09:30:00",
        "status": "confirmed",
        "created_at": now_iso,
        "cancelled_at": None,
        "cancel_reason": None,
    },
    "appt-seed-002": {
        "id": "appt-seed-002",
        "doctor_id": "doc-003",
        "doctor_name": "Dr. Laura Estrada",
        "patient_ref": "HOSP-PAT-00492",
        "patient_name": "Maria Gomez Torres",
        "specialty": "General Practitioner",
        "slot_start": "2026-03-20T11:00:00",
        "slot_end": "2026-03-20T11:30:00",
        "status": "confirmed",
        "created_at": now_iso,
        "cancelled_at": None,
        "cancel_reason": None,
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SLOT_HOURS = [9, 10, 11, 14, 15, 16]
MAX_DAYS_AHEAD = 30


def _generate_slots(doctor_id: str, days_ahead: int) -> list[dict]:
    """Return available 30-min slots for *doctor_id* over the next *days_ahead* weekdays."""
    booked = {
        appt["slot_start"]
        for appt in APPOINTMENTS.values()
        if appt["doctor_id"] == doctor_id and appt["status"] == "confirmed"
    }

    slots = []
    today = datetime.now().date()
    checked = 0
    delta = 1

    while checked < days_ahead:
        candidate = today + timedelta(days=delta)
        delta += 1
        if candidate.weekday() >= 5:  # Saturday=5, Sunday=6
            continue
        checked += 1
        for hour in SLOT_HOURS:
            start = datetime(candidate.year, candidate.month, candidate.day, hour, 0, 0)
            start_iso = start.strftime("%Y-%m-%dT%H:%M:%S")
            end_iso = (start + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S")
            if start_iso not in booked:
                slots.append({"slot_start": start_iso, "slot_end": end_iso, "available": True})

    return slots


def _appointment_out(appt: dict) -> dict:
    """Strip None fields that are optional in the response."""
    out = dict(appt)
    if out.get("cancelled_at") is None:
        out.pop("cancelled_at", None)
    if out.get("cancel_reason") is None:
        out.pop("cancel_reason", None)
    return out


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "hospital-mock-api", "version": "1.0.0"})


# 4.1 GET /doctors
@app.get("/doctors")
def list_doctors():
    area_filter = request.args.get("area", "").strip().lower()
    place_filter = request.args.get("place", "").strip().lower()

    result = []
    for doc in DOCTORS.values():
        if area_filter and area_filter not in doc["area"].lower():
            continue
        if place_filter and place_filter not in doc["place"].lower():
            continue
        result.append(doc)

    return jsonify({"data": result})


# 4.2 GET /doctors/<doctor_id>/schedule
@app.get("/doctors/<doctor_id>/schedule")
def get_doctor_schedule(doctor_id: str):
    if doctor_id not in DOCTORS:
        return jsonify({"error": "doctor not found"}), 404

    days_ahead_raw = request.args.get("days_ahead", "7")
    try:
        days_ahead = int(days_ahead_raw)
    except ValueError:
        return jsonify({"error": "days_ahead must be an integer"}), 400

    days_ahead = min(max(days_ahead, 1), MAX_DAYS_AHEAD)
    doc = DOCTORS[doctor_id]

    return jsonify(
        {
            "doctor_id": doctor_id,
            "doctor_name": doc["name"],
            "area": doc["area"],
            "place": doc["place"],
            "slots": _generate_slots(doctor_id, days_ahead),
        }
    )


# 4.3 POST /appointments
@app.post("/appointments")
def book_appointment():
    body = request.get_json(silent=True) or {}

    missing = [f for f in ("doctor_id", "patient_ref", "patient_name", "slot_start") if not body.get(f)]
    if missing:
        return jsonify({"error": f"missing required fields: {', '.join(missing)}"}), 400

    doctor_id = body["doctor_id"]
    patient_ref = body["patient_ref"]
    patient_name = body["patient_name"]
    slot_start_raw = body["slot_start"]

    try:
        slot_start_dt = datetime.fromisoformat(slot_start_raw)
    except ValueError:
        return jsonify({"error": "slot_start must be ISO 8601 format e.g. 2026-03-15T09:00:00"}), 400

    if doctor_id not in DOCTORS:
        return jsonify({"error": "doctor not found"}), 404

    slot_start_iso = slot_start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    slot_end_iso = (slot_start_dt + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S")

    for appt in APPOINTMENTS.values():
        if (
            appt["doctor_id"] == doctor_id
            and appt["slot_start"] == slot_start_iso
            and appt["status"] == "confirmed"
        ):
            return (
                jsonify({"error": f"slot {slot_start_iso} is already booked for doctor {doctor_id}"}),
                409,
            )

    doc = DOCTORS[doctor_id]
    appt_id = f"appt-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    appt = {
        "id": appt_id,
        "doctor_id": doctor_id,
        "doctor_name": doc["name"],
        "patient_ref": patient_ref,
        "patient_name": patient_name,
        "specialty": body.get("specialty") or doc["area"],
        "slot_start": slot_start_iso,
        "slot_end": slot_end_iso,
        "status": "confirmed",
        "created_at": now,
        "cancelled_at": None,
        "cancel_reason": None,
    }

    APPOINTMENTS[appt_id] = appt
    return jsonify(_appointment_out(appt)), 201


# 4.4 POST /appointments/<appt_id>/cancel
@app.post("/appointments/<appt_id>/cancel")
def cancel_appointment(appt_id: str):
    appt = APPOINTMENTS.get(appt_id)
    if appt is None:
        return jsonify({"error": "appointment not found"}), 404

    if appt["status"] == "cancelled":
        return jsonify({"error": "appointment is already cancelled"}), 409

    body = request.get_json(silent=True) or {}
    reason = body.get("reason") or "not specified"
    now = datetime.now(timezone.utc).isoformat()

    appt["status"] = "cancelled"
    appt["cancelled_at"] = now
    appt["cancel_reason"] = reason

    return jsonify(
        {
            "id": appt_id,
            "status": "cancelled",
            "cancelled_at": now,
            "reason": reason,
        }
    )


# 4.5 GET /patients/<patient_ref>/appointments
@app.get("/patients/<patient_ref>/appointments")
def get_patient_appointments(patient_ref: str):
    status_filter = request.args.get("status", "all")
    valid_statuses = {"confirmed", "cancelled", "all"}

    if status_filter not in valid_statuses:
        return jsonify({"error": "status must be one of: confirmed, cancelled, all"}), 400

    result = [
        _appointment_out(appt)
        for appt in APPOINTMENTS.values()
        if appt["patient_ref"] == patient_ref
        and (status_filter == "all" or appt["status"] == status_filter)
    ]

    result.sort(key=lambda a: a["slot_start"])

    return jsonify({"patient_ref": patient_ref, "total": len(result), "data": result})


# ---------------------------------------------------------------------------
# Generic error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"error": "method not allowed"}), 405


@app.errorhandler(Exception)
def internal_error(exc):
    app.logger.exception("Unhandled exception: %s", exc)
    return jsonify({"error": "internal server error"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
