"""Operaciones de negocio de la configuración general del sistema."""
import logging

from sqlalchemy.exc import IntegrityError

from src.core.db import db
from src.core.configuration.models import (
    Configuration,
    ID_CONFIGURACION,
    ELEMENTOS_POR_PAGINA_INICIAL,
    MANTENIMIENTO_ACTIVO_INICIAL,
)

logger = logging.getLogger(__name__)


def obtener_configuracion():
    """Devuelve la fila de configuración del sistema.

    Si la tabla está vacía, crea la fila con los valores iniciales en vez
    de fallar, para que el resto de la aplicación siempre tenga una
    configuración para leer.
    """
    configuracion = db.session.get(Configuration, ID_CONFIGURACION)
    if configuracion:
        return configuracion

    try:
        configuracion = Configuration(
            id=ID_CONFIGURACION,
            elementos_por_pagina=ELEMENTOS_POR_PAGINA_INICIAL,
            mantenimiento_activo=MANTENIMIENTO_ACTIVO_INICIAL,
        )
        db.session.add(configuracion)
        db.session.commit()
    except IntegrityError:
        # Otro pedido creó la fila al mismo tiempo: se usa esa.
        db.session.rollback()
        return db.session.get(Configuration, ID_CONFIGURACION)
    except Exception:
        db.session.rollback()
        logger.exception("No se pudo crear la configuración inicial")
        raise

    logger.info("Se creó la configuración con los valores iniciales")
    return configuracion


def actualizar_configuracion(datos):
    """Guarda los nuevos valores de la configuración y devuelve la fila.

    Recibe los datos ya validados por ``validar_configuracion``
    (``elementos_por_pagina``, ``mantenimiento_activo`` y
    ``mensaje_mantenimiento``). Ante un error hace rollback y relanza
    la excepción.
    """
    configuracion = obtener_configuracion()

    try:
        configuracion.elementos_por_pagina = datos["elementos_por_pagina"]
        configuracion.mantenimiento_activo = datos["mantenimiento_activo"]
        configuracion.mensaje_mantenimiento = datos["mensaje_mantenimiento"]
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("No se pudo actualizar la configuración")
        raise

    logger.info("Configuración actualizada: %s", configuracion)
    return configuracion
