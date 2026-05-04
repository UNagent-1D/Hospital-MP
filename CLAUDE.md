# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Mock REST API for a hospital appointment booking system, designed for AI agent consumption and integration testing. It intentionally has no persistence, no authentication, and no production WSGI server — these are documented limitations, not bugs.

## Commands

```bash
# Local development
python app.py                        # Starts Flask dev server on 0.0.0.0:8080

# Docker (recommended)
docker compose up --build            # Build and run containerized service

# Tests
pytest test_app.py -v                # Run full test suite
pytest test_app.py -v -k "test_name" # Run a single test by name
```

## Architecture

**Single-file Flask API** — all logic lives in [app.py](app.py) (~317 lines). No database; state is stored in two in-memory Python dicts:

- `DOCTORS` — 5 hardcoded doctors (id, name, area, phone, place). Read-only at runtime.
- `APPOINTMENTS` — seed data + runtime bookings. Resets on every server restart.

**Request flow:** HTTP request → Flask route → mutate/read global dict → JSON response. No middleware, no service layer, no ORM.

**Key helpers:**
- `_generate_slots()` — produces 30-min availability windows (09:00–16:00, weekdays only, up to 30 days ahead)
- `_appointment_out()` — strips null fields before serializing responses

## Endpoints Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/doctors` | List all doctors |
| GET | `/doctors/{id}/schedule` | Available slots for a doctor |
| POST | `/appointments` | Book an appointment |
| GET | `/patients/{ref}/appointments` | List patient appointments |
| POST | `/appointments/{id}/cancel` | Cancel an appointment |

All responses are `application/json`. Status codes: 200, 201, 400, 404, 409, 500.

## Testing Conventions

Tests use a pytest autouse fixture that **resets `APPOINTMENTS` to seed state before each test** — this is critical for isolation. Tests cover happy path, validation errors, conflict detection (409), and cancellation flows. When adding routes or logic, follow the same fixture pattern in [test_app.py](test_app.py).

## Known Intentional Limitations

- No data persistence (RAM only — data is lost on restart)
- No authentication or authorization
- No concurrency control (race conditions possible under concurrent load)
- No timezone handling (UTC assumed throughout)
- No production WSGI server (Flask dev server only)
