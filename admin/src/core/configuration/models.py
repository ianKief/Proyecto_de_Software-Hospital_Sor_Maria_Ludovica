"""Modelo de la configuración general del sistema."""
from datetime import datetime, timezone
from src.core.db import db
from sqlalchemy import CheckConstraint


# La tabla tiene una sola fila y siempre usa este id.
ID_CONFIGURACION = 1

# Valores iniciales de la configuración (los usan el modelo, las operaciones y el seed).
ELEMENTOS_POR_PAGINA_INICIAL = 25
MANTENIMIENTO_ACTIVO_INICIAL = False


class Configuration(db.Model):
    """Parámetros generales del sistema. La tabla tiene una sola fila.

    Guarda cuántos elementos se muestran por página en los listados
    y si el sitio está en modo mantenimiento, con el mensaje a mostrar.
    """
    __tablename__ = 'configuration'

    id = db.Column(db.Integer, primary_key=True)
    elementos_por_pagina = db.Column(db.Integer, nullable=False, default=ELEMENTOS_POR_PAGINA_INICIAL)
    mantenimiento_activo = db.Column(db.Boolean, nullable=False, default=MANTENIMIENTO_ACTIVO_INICIAL)
    mensaje_mantenimiento = db.Column(db.String(255), nullable=True)

    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint('elementos_por_pagina BETWEEN 1 AND 25', name='chk_configuration_elementos_por_pagina'),
    )

    def __repr__(self):
        """Devuelve una representación corta, útil para depurar."""
        return f'<Configuration elementos_por_pagina:{self.elementos_por_pagina} mantenimiento:{self.mantenimiento_activo}>'
