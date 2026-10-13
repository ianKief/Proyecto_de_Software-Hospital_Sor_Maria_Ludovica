BEGIN;

CREATE TABLE IF NOT EXISTS cargas (
    id SERIAL PRIMARY KEY,
    creado_por INTEGER NOT NULL REFERENCES users(id),
    periodicidad VARCHAR(20) NOT NULL,
    fecha_desde DATE NOT NULL,
    fecha_hasta DATE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE
        NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS carga_id INTEGER;

-- Asigna una carga diaria a cada pedido histórico
-- que todavía no tenga una carga asociada.
DO $$
DECLARE
    pedido_actual RECORD;
    nueva_carga_id INTEGER;
BEGIN
    FOR pedido_actual IN
        SELECT id, creado_por, fecha
        FROM pedidos
        WHERE carga_id IS NULL
    LOOP
        INSERT INTO cargas (
            creado_por,
            periodicidad,
            fecha_desde,
            fecha_hasta
        )
        VALUES (
            pedido_actual.creado_por,
            'diaria',
            pedido_actual.fecha,
            pedido_actual.fecha
        )
        RETURNING id INTO nueva_carga_id;

        UPDATE pedidos
        SET carga_id = nueva_carga_id
        WHERE id = pedido_actual.id;
    END LOOP;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = ANY(c.conkey)
        WHERE c.conrelid = 'pedidos'::regclass
          AND c.confrelid = 'cargas'::regclass
          AND c.contype = 'f'
          AND a.attname = 'carga_id'
    ) THEN
        ALTER TABLE pedidos
            ADD CONSTRAINT fk_pedidos_carga_id
            FOREIGN KEY (carga_id) REFERENCES cargas(id);
    END IF;
END $$;

ALTER TABLE pedidos
    ALTER COLUMN carga_id SET NOT NULL;

COMMIT;