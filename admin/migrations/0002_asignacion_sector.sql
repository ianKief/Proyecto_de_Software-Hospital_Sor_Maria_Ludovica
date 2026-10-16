BEGIN;

CREATE TABLE IF NOT EXISTS asignacion_sector (
    id SERIAL PRIMARY KEY,
    personal_id INTEGER NOT NULL REFERENCES personnel(id),
    sector_id INTEGER NOT NULL REFERENCES sectors(id),
    fecha_desde DATE NOT NULL,
    fecha_hasta DATE,
    CONSTRAINT ck_asignacion_sector_fechas
        CHECK (fecha_hasta IS NULL OR fecha_hasta >= fecha_desde)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_asignacion_sector_activa
    ON asignacion_sector (personal_id)
    WHERE fecha_hasta IS NULL;

-- Registrar la asignación actual de quienes todavía no tienen historial.
-- La fecha inicial es hoy porque no conocemos la fecha histórica real.
INSERT INTO asignacion_sector (
    personal_id,
    sector_id,
    fecha_desde
)
SELECT
    p.id,
    p.sector_id,
    CURRENT_DATE
FROM personnel p
WHERE p.sector_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM asignacion_sector a
      WHERE a.personal_id = p.id
        AND a.fecha_hasta IS NULL
  );

COMMIT;