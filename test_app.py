import pytest


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "hospital-mock-api"


# ---------------------------------------------------------------------------
# GET /doctors
# ---------------------------------------------------------------------------

def test_list_doctors_returns_all(client):
    res = client.get("/doctors")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["data"]) == 5


def test_list_doctors_filter_by_area(client):
    res = client.get("/doctors?area=Pediatrician")
    assert res.status_code == 200
    doctors = res.get_json()["data"]
    assert all("Pediatrician" in d["area"] for d in doctors)
    assert len(doctors) == 2


def test_list_doctors_filter_no_match(client):
    res = client.get("/doctors?area=Oncologist")
    assert res.status_code == 200
    assert res.get_json()["data"] == []


# ---------------------------------------------------------------------------
# GET /doctors/<doctor_id>/schedule
# ---------------------------------------------------------------------------

def test_get_schedule_valid(client):
    res = client.get("/doctors/doc-001/schedule?days_ahead=3")
    assert res.status_code == 200
    data = res.get_json()
    assert data["doctor_id"] == "doc-001"
    assert isinstance(data["slots"], list)
    assert len(data["slots"]) > 0


def test_get_schedule_doctor_not_found(client):
    res = client.get("/doctors/doc-999/schedule")
    assert res.status_code == 404


def test_get_schedule_invalid_days_ahead(client):
    res = client.get("/doctors/doc-001/schedule?days_ahead=abc")
    assert res.status_code == 400


def test_get_schedule_booked_slot_not_in_slots(client):
    # Book a slot then verify it no longer appears as available
    slot = client.get("/doctors/doc-002/schedule?days_ahead=3").get_json()["slots"][0]["slot_start"]
    client.post("/appointments", json={
        "doctor_id": "doc-002",
        "patient_ref": "HOSP-PAT-TEST",
        "patient_name": "Test Patient",
        "slot_start": slot,
    })
    slots_after = client.get("/doctors/doc-002/schedule?days_ahead=3").get_json()["slots"]
    assert all(s["slot_start"] != slot for s in slots_after)


# ---------------------------------------------------------------------------
# POST /appointments
# ---------------------------------------------------------------------------

def _first_available_slot(client, doctor_id="doc-002"):
    return client.get(f"/doctors/{doctor_id}/schedule?days_ahead=5").get_json()["slots"][0]["slot_start"]


def test_book_appointment_success(client):
    slot = _first_available_slot(client)
    res = client.post("/appointments", json={
        "doctor_id": "doc-002",
        "patient_ref": "HOSP-PAT-111",
        "patient_name": "Ana Lopez",
        "slot_start": slot,
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "confirmed"
    assert data["doctor_id"] == "doc-002"
    assert "id" in data


def test_book_appointment_missing_fields(client):
    res = client.post("/appointments", json={"doctor_id": "doc-001"})
    assert res.status_code == 400
    assert "missing required fields" in res.get_json()["error"]


def test_book_appointment_doctor_not_found(client):
    res = client.post("/appointments", json={
        "doctor_id": "doc-999",
        "patient_ref": "HOSP-PAT-111",
        "patient_name": "Ana Lopez",
        "slot_start": "2026-05-01T09:00:00",
    })
    assert res.status_code == 404


def test_book_appointment_invalid_slot_format(client):
    res = client.post("/appointments", json={
        "doctor_id": "doc-001",
        "patient_ref": "HOSP-PAT-111",
        "patient_name": "Ana Lopez",
        "slot_start": "not-a-date",
    })
    assert res.status_code == 400


def test_book_appointment_double_booking(client):
    slot = _first_available_slot(client)
    payload = {
        "doctor_id": "doc-002",
        "patient_ref": "HOSP-PAT-111",
        "patient_name": "Ana Lopez",
        "slot_start": slot,
    }
    client.post("/appointments", json=payload)
    res = client.post("/appointments", json=payload)
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# POST /appointments/<appt_id>/cancel
# ---------------------------------------------------------------------------

def test_cancel_appointment_success(client):
    slot = _first_available_slot(client)
    appt_id = client.post("/appointments", json={
        "doctor_id": "doc-002",
        "patient_ref": "HOSP-PAT-222",
        "patient_name": "Luis Mora",
        "slot_start": slot,
    }).get_json()["id"]

    res = client.post(f"/appointments/{appt_id}/cancel", json={"reason": "no puede asistir"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "cancelled"
    assert data["reason"] == "no puede asistir"


def test_cancel_appointment_not_found(client):
    res = client.post("/appointments/appt-fake-id/cancel", json={})
    assert res.status_code == 404


def test_cancel_appointment_already_cancelled(client):
    slot = _first_available_slot(client)
    appt_id = client.post("/appointments", json={
        "doctor_id": "doc-002",
        "patient_ref": "HOSP-PAT-333",
        "patient_name": "Rosa Gil",
        "slot_start": slot,
    }).get_json()["id"]

    client.post(f"/appointments/{appt_id}/cancel", json={})
    res = client.post(f"/appointments/{appt_id}/cancel", json={})
    assert res.status_code == 409


def test_cancel_without_reason_defaults(client):
    slot = _first_available_slot(client)
    appt_id = client.post("/appointments", json={
        "doctor_id": "doc-002",
        "patient_ref": "HOSP-PAT-444",
        "patient_name": "Pedro Ruiz",
        "slot_start": slot,
    }).get_json()["id"]

    res = client.post(f"/appointments/{appt_id}/cancel", json={})
    assert res.status_code == 200
    assert res.get_json()["reason"] == "not specified"


# ---------------------------------------------------------------------------
# GET /patients/<patient_ref>/appointments
# ---------------------------------------------------------------------------

def test_get_patient_appointments(client):
    res = client.get("/patients/HOSP-PAT-00492/appointments")
    assert res.status_code == 200
    data = res.get_json()
    assert data["patient_ref"] == "HOSP-PAT-00492"
    assert data["total"] == 2


def test_get_patient_appointments_filter_confirmed(client):
    res = client.get("/patients/HOSP-PAT-00492/appointments?status=confirmed")
    assert res.status_code == 200
    appts = res.get_json()["data"]
    assert all(a["status"] == "confirmed" for a in appts)


def test_get_patient_appointments_filter_cancelled(client):
    slot = _first_available_slot(client)
    appt_id = client.post("/appointments", json={
        "doctor_id": "doc-002",
        "patient_ref": "HOSP-PAT-00492",
        "patient_name": "Maria Gomez Torres",
        "slot_start": slot,
    }).get_json()["id"]
    client.post(f"/appointments/{appt_id}/cancel", json={})

    res = client.get("/patients/HOSP-PAT-00492/appointments?status=cancelled")
    assert res.status_code == 200
    appts = res.get_json()["data"]
    assert all(a["status"] == "cancelled" for a in appts)
    assert len(appts) == 1


def test_get_patient_appointments_invalid_status(client):
    res = client.get("/patients/HOSP-PAT-00492/appointments?status=unknown")
    assert res.status_code == 400


def test_get_patient_no_appointments(client):
    res = client.get("/patients/HOSP-PAT-NONE/appointments")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 0
    assert data["data"] == []
