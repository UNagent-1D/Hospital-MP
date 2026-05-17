import json
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, Response, g, jsonify, request
from dotenv import load_dotenv
from db import get_db

import channel as secure_channel

load_dotenv()

app = Flask(__name__)
secure_channel.init_from_env()


# ---------------------------------------------------------------------------
# Secure-channel hooks
# ---------------------------------------------------------------------------
# Backend callers (chat-orch, conversation-chat) wrap their JSON bodies in
# an AES-256-GCM envelope and tag the request with `X-Secure-Channel:
# aes256gcm/1`. We decrypt the body before the route handler runs so handlers
# can keep using `request.get_json()` unchanged, and we re-encrypt the
# response on the way out so the wire stays opaque end to end.
#
# Plaintext callers (the /health endpoint, anyone without the header) are
# passed through unchanged.


@app.before_request
def _secure_channel_decrypt() -> Response | None:
    if request.path == "/health":
        return None
    ct = (request.headers.get("Content-Type") or "").lower()
    has_header = request.headers.get(secure_channel.HEADER_NAME) is not None
    body_is_envelope = ct.startswith(secure_channel.CONTENT_TYPE)
    if not has_header and not body_is_envelope:
        g.secure_inbound = False
        return None
    # If the caller signalled the channel via the header but didn't send an
    # envelope body (typical for GETs and other bodyless verbs), there's
    # nothing to decrypt — just mark the request so the response gets sealed.
    raw = request.get_data()
    if not body_is_envelope or len(raw) == 0:
        g.secure_inbound = True
        return None
    try:
        envelope = json.loads(raw.decode("utf-8"))
        plain = secure_channel.open_envelope(envelope)
    except (json.JSONDecodeError, secure_channel.ChannelError) as e:
        return jsonify({"error": "secure_channel_decrypt_failed", "detail": str(e)}), 400
    # Stash the plaintext directly into Flask's body cache so handlers can
    # call `request.get_data()` / `request.get_json()` unchanged. We bypass
    # Werkzeug's stream wrapping (which would otherwise re-read the original
    # ciphertext from wsgi.input) by populating the caches.
    try:
        parsed = json.loads(plain.decode("utf-8")) if plain else None
    except json.JSONDecodeError:
        parsed = None
    request._cached_data = plain  # type: ignore[attr-defined]
    # Flask's _cached_json is a 2-tuple keyed by `silent` (False, True). Both
    # entries hold the parsed value; on silent=True a parse failure becomes
    # None instead of raising.
    request._cached_json = (parsed, parsed)  # type: ignore[attr-defined]
    g.secure_inbound = True
    return None


@app.after_request
def _secure_channel_encrypt(response: Response) -> Response:
    if not getattr(g, "secure_inbound", False):
        return response
    if response.direct_passthrough:
        # Streamed responses skip the envelope — none of Hospital-MP's
        # endpoints stream today, but this keeps the hook safe if one is
        # added later.
        return response
    body = response.get_data()
    sealed_body, ct, _ = secure_channel.seal_json(json.loads(body) if body else {})
    response.set_data(sealed_body)
    response.mimetype = secure_channel.CONTENT_TYPE
    response.headers["Content-Type"] = ct
    response.headers[secure_channel.HEADER_NAME] = secure_channel.HEADER_VALUE
    return response


# Small wrapper so the WSGI environ can hold the decrypted body as a stream.
class _BytesIO:
    def __init__(self, data: bytes) -> None:
        self._buf = data
        self._pos = 0

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            chunk = self._buf[self._pos :]
            self._pos = len(self._buf)
            return chunk
        chunk = self._buf[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk

    def readline(self, n: int = -1) -> bytes:  # noqa: ARG002 — flask sniffs presence
        nl = self._buf.find(b"\n", self._pos)
        if nl == -1:
            return self.read()
        chunk = self._buf[self._pos : nl + 1]
        self._pos = nl + 1
        return chunk

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SLOT_HOURS = [9, 10, 11, 14, 15, 16]
MAX_DAYS_AHEAD = 30


def _generate_slots(booked: set, days_ahead: int) -> list:
    """Return available 30-min slots given a set of already-booked slot_start strings."""
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
    area_filter = request.args.get("area", "").strip()
    place_filter = request.args.get("place", "").strip()

    query = get_db().table("doctors").select("*")
    if area_filter:
        query = query.ilike("area", f"%{area_filter}%")
    if place_filter:
        query = query.ilike("place", f"%{place_filter}%")

    result = query.execute()
    return jsonify({"data": result.data})


# 4.2 GET /doctors/<doctor_id>/schedule
@app.get("/doctors/<doctor_id>/schedule")
def get_doctor_schedule(doctor_id: str):
    db = get_db()
    doc_res = db.table("doctors").select("*").eq("id", doctor_id).execute()
    if not doc_res.data:
        return jsonify({"error": "doctor not found"}), 404

    days_ahead_raw = request.args.get("days_ahead", "7")
    try:
        days_ahead = int(days_ahead_raw)
    except ValueError:
        return jsonify({"error": "days_ahead must be an integer"}), 400

    days_ahead = min(max(days_ahead, 1), MAX_DAYS_AHEAD)
    doc = doc_res.data[0]

    booked_res = (
        db.table("appointments")
        .select("slot_start")
        .eq("doctor_id", doctor_id)
        .eq("status", "confirmed")
        .execute()
    )
    booked = {row["slot_start"] for row in booked_res.data}

    return jsonify(
        {
            "doctor_id": doctor_id,
            "doctor_name": doc["name"],
            "area": doc["area"],
            "place": doc["place"],
            "slots": _generate_slots(booked, days_ahead),
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

    db = get_db()
    doc_res = db.table("doctors").select("*").eq("id", doctor_id).execute()
    if not doc_res.data:
        return jsonify({"error": "doctor not found"}), 404

    slot_start_iso = slot_start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    slot_end_iso = (slot_start_dt + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S")

    conflict = (
        db.table("appointments")
        .select("id")
        .eq("doctor_id", doctor_id)
        .eq("slot_start", slot_start_iso)
        .eq("status", "confirmed")
        .execute()
    )
    if conflict.data:
        return jsonify({"error": f"slot {slot_start_iso} is already booked for doctor {doctor_id}"}), 409

    doc = doc_res.data[0]
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

    db.table("appointments").insert(appt).execute()
    return jsonify(_appointment_out(appt)), 201


# 4.4 POST /appointments/<appt_id>/cancel
@app.post("/appointments/<appt_id>/cancel")
def cancel_appointment(appt_id: str):
    db = get_db()
    appt_res = db.table("appointments").select("*").eq("id", appt_id).execute()
    if not appt_res.data:
        return jsonify({"error": "appointment not found"}), 404

    appt = appt_res.data[0]
    if appt["status"] == "cancelled":
        return jsonify({"error": "appointment is already cancelled"}), 409

    body = request.get_json(silent=True) or {}
    reason = body.get("reason") or "not specified"
    now = datetime.now(timezone.utc).isoformat()

    db.table("appointments").update(
        {"status": "cancelled", "cancelled_at": now, "cancel_reason": reason}
    ).eq("id", appt_id).execute()

    return jsonify({"id": appt_id, "status": "cancelled", "cancelled_at": now, "reason": reason})


# 4.5 GET /patients/<patient_ref>/appointments
@app.get("/patients/<patient_ref>/appointments")
def get_patient_appointments(patient_ref: str):
    status_filter = request.args.get("status", "all")
    valid_statuses = {"confirmed", "cancelled", "all"}

    if status_filter not in valid_statuses:
        return jsonify({"error": "status must be one of: confirmed, cancelled, all"}), 400

    db = get_db()
    query = db.table("appointments").select("*").eq("patient_ref", patient_ref)
    if status_filter != "all":
        query = query.eq("status", status_filter)

    result = query.order("slot_start", desc=False).execute()
    data = [_appointment_out(appt) for appt in result.data]

    return jsonify({"patient_ref": patient_ref, "total": len(data), "data": data})


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
