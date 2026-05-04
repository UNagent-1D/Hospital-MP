INSERT INTO doctors (id, name, area, phone, place) VALUES
  ('doc-001', 'Dr. Alejandra Rios',  'Cardiologist',        '+573101234567', 'Bogota Norte — Clínica San Ignacio, Room 4A'),
  ('doc-002', 'Dr. Carlos Mendoza',  'Pediatrician',         '+573107654321', 'Bogota Sur — Torre Médica Central, Floor 2'),
  ('doc-003', 'Dr. Laura Estrada',   'General Practitioner', '+573109876543', 'Medellin Centro — Centro Médico Poblado, Room 101'),
  ('doc-004', 'Dr. Marcos Villegas', 'Neurologist',          '+573102345678', 'Bogota Norte — Clínica San Ignacio, Neurology Wing, Room 7'),
  ('doc-005', 'Dr. Sofia Herrera',   'Pediatrician',         '+573108765432', 'Bogota Sur — Hospital El Tunal, Pediatrics Block B')
ON CONFLICT (id) DO NOTHING;

INSERT INTO appointments (id, doctor_id, doctor_name, patient_ref, patient_name, specialty, slot_start, slot_end, status, created_at) VALUES
  ('appt-seed-001', 'doc-001', 'Dr. Alejandra Rios', 'HOSP-PAT-00492', 'Maria Gomez Torres', 'Cardiologist',        '2026-03-15T09:00:00', '2026-03-15T09:30:00', 'confirmed', NOW()::TEXT),
  ('appt-seed-002', 'doc-003', 'Dr. Laura Estrada',  'HOSP-PAT-00492', 'Maria Gomez Torres', 'General Practitioner','2026-03-20T11:00:00', '2026-03-20T11:30:00', 'confirmed', NOW()::TEXT)
ON CONFLICT (id) DO NOTHING;
