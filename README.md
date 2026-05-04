# Hospital-MP — Mock API REST

API REST simulada de un hospital, diseñada para ser consumida por agentes de IA u otros servicios como mock durante desarrollo y pruebas.

---

## Base de datos

El servicio soporta dos backends de base de datos. La variable `DATABASE_URL` tiene prioridad sobre las credenciales de Supabase.

| Variable | Backend |
|----------|---------|
| `DATABASE_URL` | PostgreSQL directo (local o remoto) |
| `SUPABASE_URL` + `SUPABASE_KEY` | Supabase cloud |

---

## Levantar el servicio

### Opción 1 — Docker Compose con PostgreSQL local (recomendado)

No requiere configuración. El compose levanta postgres, aplica el esquema y carga los datos semilla automáticamente.

```bash
docker compose up --build
```

El servicio queda disponible en `http://localhost:8080`.

### Opción 2 — Python local contra Supabase

1. Crear un proyecto en [supabase.com](https://supabase.com).
2. Ejecutar `schema.sql` en el SQL Editor del proyecto.
3. Crear el archivo `.env` con las credenciales:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
```

4. Cargar datos iniciales y arrancar:

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

### Opción 3 — Python local contra PostgreSQL local

```bash
pip install -r requirements.txt
```

Crear el archivo `.env`:

```env
DATABASE_URL=postgresql://hospital:hospital@localhost:5432/hospital
```

Iniciar postgres (si no está corriendo), aplicar el esquema y el seed:

```bash
psql $DATABASE_URL -f schema.sql
psql $DATABASE_URL -f seed.sql
python app.py
```

Requiere Python 3.12+.

---

## Tests

Los tests usan un cliente de base de datos en memoria y no requieren ninguna conexión real.

```bash
pytest test_app.py -v
```

Para correr un test individual:

```bash
pytest test_app.py -v -k "test_book_appointment_success"
```

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

## Probar los endpoints

```bash
curl http://localhost:8080/health

# Listar médicos
curl http://localhost:8080/doctors
curl "http://localhost:8080/doctors?area=Cardiologist"

# Ver slots disponibles
curl "http://localhost:8080/doctors/doc-001/schedule?days_ahead=5"

# Agendar una cita
curl -X POST http://localhost:8080/appointments \
  -H "Content-Type: application/json" \
  -d '{"doctor_id":"doc-001","patient_ref":"HOSP-PAT-00001","patient_name":"Juan Perez","slot_start":"2026-04-21T09:00:00"}'

# Ver citas de un paciente
curl http://localhost:8080/patients/HOSP-PAT-00001/appointments

# Cancelar una cita (reemplazar <appt_id>)
curl -X POST http://localhost:8080/appointments/<appt_id>/cancel \
  -H "Content-Type: application/json" \
  -d '{"reason": "El paciente no puede asistir"}'
```

---

## Datos semilla

Al iniciar, el servicio carga:

- **5 médicos** (`doc-001` a `doc-005`) con especialidades: Cardiología, Pediatría, Medicina General, Neurología.
- **2 citas confirmadas** de ejemplo para el paciente `HOSP-PAT-00492`.

Con Docker Compose, la carga ocurre automáticamente la primera vez. Con PostgreSQL local o Supabase, ejecutar `seed.sql` o `seed.py` respectivamente.

---

## Limitaciones

- **Sin autenticación**: cualquier cliente puede leer y modificar datos sin credenciales.
- **Sin validación de horarios**: el API no verifica que el `slot_start` solicitado sea un slot válido del médico; solo comprueba que no esté ya reservado.
- **Slots fijos**: los horarios disponibles son siempre 09:00, 10:00, 11:00, 14:00, 15:00 y 16:00, de lunes a viernes, hasta 30 días adelante.
- **Sin concurrencia**: no hay manejo de condiciones de carrera si dos peticiones reservan el mismo slot simultáneamente.
- **Un solo proceso**: el servidor corre con `python app.py` (Flask desarrollo); no está configurado con un servidor WSGI de producción como Gunicorn.
