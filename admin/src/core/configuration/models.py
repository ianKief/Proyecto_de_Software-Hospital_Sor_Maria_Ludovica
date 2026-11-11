"""Modelo de la configuración general del sistema."""
from datetime import datetime, time, timezone
from src.core.db import db
from sqlalchemy import CheckConstraint


# La tabla tiene una sola fila y siempre usa este id.
ID_CONFIGURACION = 1

# Valores iniciales de la configuración (los usan el modelo, las operaciones y el seed).
ELEMENTOS_POR_PAGINA_INICIAL = 25
MANTENIMIENTO_ACTIVO_INICIAL = False

# Horarios iniciales de cada comida: por ahora son los mismos que TURNOS en
# core/deliveries/turnos.py. En la tarea CF7 turnos.py pasa a leerlos de esta tabla.
DESAYUNO_INICIO_INICIAL = time(6, 0)
DESAYUNO_FIN_INICIAL = time(10, 0)
ALMUERZO_INICIO_INICIAL = time(11, 30)
ALMUERZO_FIN_INICIAL = time(15, 0)
MERIENDA_INICIO_INICIAL = time(16, 0)
MERIENDA_FIN_INICIAL = time(18, 30)
CENA_INICIO_INICIAL = time(20, 0)
CENA_FIN_INICIAL = time(23, 0)

# Propuesta (a confirmar con el equipo): los pedidos se cierran a las 20:00 del día anterior.
HORARIO_CORTE_INICIAL = time(20, 0)


class Configuration(db.Model):
    """Parámetros generales del sistema. La tabla tiene una sola fila.

    Guarda cuántos elementos se muestran por página en los listados
    y si el sitio está en modo mantenimiento, con el mensaje a mostrar.

    También guarda el horario de inicio y fin de cada comida (desayuno,
    almuerzo, merienda y cena), todos dentro del mismo día, y el horario
    de corte de pedidos: la hora límite del **día anterior** a la fecha
    del pedido hasta la que se puede cargarlo o modificarlo. Por ejemplo,
    con corte 20:00, un pedido para el jueves se acepta hasta el
    miércoles a las 20:00.
    """
    __tablename__ = 'configuration'

    id = db.Column(db.Integer, primary_key=True)
    elementos_por_pagina = db.Column(db.Integer, nullable=False, default=ELEMENTOS_POR_PAGINA_INICIAL)
    mantenimiento_activo = db.Column(db.Boolean, nullable=False, default=MANTENIMIENTO_ACTIVO_INICIAL)
    mensaje_mantenimiento = db.Column(db.String(255), nullable=True)

    desayuno_inicio = db.Column(db.Time, nullable=False, default=DESAYUNO_INICIO_INICIAL)
    desayuno_fin = db.Column(db.Time, nullable=False, default=DESAYUNO_FIN_INICIAL)
    almuerzo_inicio = db.Column(db.Time, nullable=False, default=ALMUERZO_INICIO_INICIAL)
    almuerzo_fin = db.Column(db.Time, nullable=False, default=ALMUERZO_FIN_INICIAL)
    merienda_inicio = db.Column(db.Time, nullable=False, default=MERIENDA_INICIO_INICIAL)
    merienda_fin = db.Column(db.Time, nullable=False, default=MERIENDA_FIN_INICIAL)
    cena_inicio = db.Column(db.Time, nullable=False, default=CENA_INICIO_INICIAL)
    cena_fin = db.Column(db.Time, nullable=False, default=CENA_FIN_INICIAL)
    horario_corte = db.Column(db.Time, nullable=False, default=HORARIO_CORTE_INICIAL)

    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint('elementos_por_pagina BETWEEN 1 AND 25', name='chk_configuration_elementos_por_pagina'),
    )

    def __repr__(self):
        """Devuelve una representación corta, útil para depurar."""
        return f'<Configuration elementos_por_pagina:{self.elementos_por_pagina} mantenimiento:{self.mantenimiento_activo}>'
