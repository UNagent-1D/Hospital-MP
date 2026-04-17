# Hospital-MP — Mock API REST

API REST simulada de un hospital, diseñada para ser consumida por agentes de IA u otros servicios como mock durante desarrollo y pruebas.

---

## Levantar el servicio

### Opción 1 — Docker Compose (recomendado)

```bash
docker compose up --build
```

El servicio queda disponible en `http://localhost:8080`.

### Opción 2 — Python local

```bash
pip install -r requirements.txt
python app.py
```

Requiere Python 3.12+.

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio |
| `GET` | `/doctors` | Lista médicos (filtros: `?area=` `?place=`) |
| `GET` | `/doctors/{doctor_id}/schedule` | Slots disponibles del médico (`?days_ahead=7`) |
| `POST` | `/appointments` | Agendar una cita |
| `POST` | `/appointments/{appt_id}/cancel` | Cancelar una cita |
| `GET` | `/patients/{patient_ref}/appointments` | Citas de un paciente (`?status=confirmed\|cancelled\|all`) |

### POST `/appointments` — body esperado

```json
{
  "doctor_id": "doc-001",
  "patient_ref": "HOSP-PAT-00492",
  "patient_name": "Maria Gomez Torres",
  "slot_start": "2026-04-20T09:00:00",
  "specialty": "Cardiologist"
}
```

### POST `/appointments/{id}/cancel` — body esperado

```json
{
  "reason": "El paciente no puede asistir"
}
```

---

## Correr los tests

```bash
pip install pytest
pytest test_app.py -v
```

---

## Verificar que el servicio está activo

```bash
curl http://localhost:8080/health
```

Respuesta esperada:

```json
{"service": "hospital-mock-api", "status": "ok", "version": "1.0.0"}
```

---

## Probar los endpoints

### Listar médicos

```bash
curl http://localhost:8080/doctors
```

Filtrar por especialidad:

```bash
curl "http://localhost:8080/doctors?area=Cardiologist"
```

### Ver slots disponibles de un médico

```bash
curl "http://localhost:8080/doctors/doc-001/schedule?days_ahead=5"
```

### Agendar una cita

```bash
curl -X POST http://localhost:8080/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "doctor_id": "doc-001",
    "patient_ref": "HOSP-PAT-00001",
    "patient_name": "Juan Perez",
    "slot_start": "2026-04-21T09:00:00"
  }'
```

### Ver citas de un paciente

```bash
curl http://localhost:8080/patients/HOSP-PAT-00001/appointments
```

### Cancelar una cita

Reemplaza `<appt_id>` con el `id` retornado al agendar:

```bash
curl -X POST http://localhost:8080/appointments/<appt_id>/cancel \
  -H "Content-Type: application/json" \
  -d '{"reason": "El paciente no puede asistir"}'
```

---

## Datos semilla

Al iniciar, el servicio carga:

- **5 médicos** (`doc-001` a `doc-005`) con especialidades: Cardiología, Pediatría, Medicina General, Neurología.
- **2 citas confirmadas** de ejemplo para el paciente `HOSP-PAT-00492`.

---

## Limitaciones

- **Sin persistencia**: todos los datos viven en memoria RAM. Al reiniciar el servidor, el estado vuelve al semilla original.
- **Sin autenticación**: cualquier cliente puede leer y modificar datos sin credenciales.
- **Sin validación de horarios**: el API no verifica que el `slot_start` solicitado sea un slot válido del médico; solo comprueba que no esté ya reservado.
- **Slots fijos**: los horarios disponibles son siempre 09:00, 10:00, 11:00, 14:00, 15:00 y 16:00, de lunes a viernes, hasta 30 días adelante.
- **Sin concurrencia**: no hay manejo de condiciones de carrera si dos peticiones reservan el mismo slot simultáneamente.
- **Un solo proceso**: el servidor corre con `python app.py` (Flask desarrollo); no está configurado con un servidor WSGI de producción como Gunicorn.
