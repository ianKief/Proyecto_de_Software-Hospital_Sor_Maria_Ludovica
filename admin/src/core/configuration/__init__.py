"""Operaciones de negocio de la configuración general del sistema."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from src.core.db import db
from src.core.configuration.models import (
    Configuration,
    ID_CONFIGURACION,
    ELEMENTOS_POR_PAGINA_INICIAL,
    MANTENIMIENTO_ACTIVO_INICIAL,
    DESAYUNO_INICIO_INICIAL,
    DESAYUNO_FIN_INICIAL,
    ALMUERZO_INICIO_INICIAL,
    ALMUERZO_FIN_INICIAL,
    MERIENDA_INICIO_INICIAL,
    MERIENDA_FIN_INICIAL,
    CENA_INICIO_INICIAL,
    CENA_FIN_INICIAL,
    HORARIO_CORTE_INICIAL,
)

logger = logging.getLogger(__name__)

# Argentina usa UTC-3 todo el año (no tiene horario de verano).
# Se arma a mano para no depender de zoneinfo, que en Windows necesita instalar tzdata.
# Vive acá y no en Entregas porque turnos.py ya importa este módulo:
# si este módulo importara turnos.py, el import sería circular.
ZONA_ARGENTINA = timezone(timedelta(hours=-3))


def hora_a_texto(hora):
    """Devuelve una hora (``datetime.time``) como texto "HH:MM".

    Es el formato que usan el ``<input type="time">`` del formulario de
    Ajustes y la API (sin segundos, que ``str(hora)`` sí mostraría).
    """
    return hora.strftime("%H:%M")


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
            desayuno_inicio=DESAYUNO_INICIO_INICIAL,
            desayuno_fin=DESAYUNO_FIN_INICIAL,
            almuerzo_inicio=ALMUERZO_INICIO_INICIAL,
            almuerzo_fin=ALMUERZO_FIN_INICIAL,
            merienda_inicio=MERIENDA_INICIO_INICIAL,
            merienda_fin=MERIENDA_FIN_INICIAL,
            cena_inicio=CENA_INICIO_INICIAL,
            cena_fin=CENA_FIN_INICIAL,
            horario_corte=HORARIO_CORTE_INICIAL,
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


def _guardar_horarios(configuracion, datos):
    """Copia a la configuración los 9 horarios (``datetime.time``) ya validados.

    No hace commit: lo hace ``actualizar_configuracion``, junto con el resto
    de los campos, para que todo se guarde o nada.
    """
    configuracion.desayuno_inicio = datos["desayuno_inicio"]
    configuracion.desayuno_fin = datos["desayuno_fin"]
    configuracion.almuerzo_inicio = datos["almuerzo_inicio"]
    configuracion.almuerzo_fin = datos["almuerzo_fin"]
    configuracion.merienda_inicio = datos["merienda_inicio"]
    configuracion.merienda_fin = datos["merienda_fin"]
    configuracion.cena_inicio = datos["cena_inicio"]
    configuracion.cena_fin = datos["cena_fin"]
    configuracion.horario_corte = datos["horario_corte"]


def actualizar_configuracion(datos, usuario):
    """Guarda los nuevos valores de la configuración y devuelve la fila.

    Recibe los datos ya validados por ``validar_configuracion``
    (``elementos_por_pagina``, ``mantenimiento_activo``,
    ``mensaje_mantenimiento`` y los 9 horarios de comidas y de corte)
    y el email del usuario que hace el cambio, que se registra en el log
    junto con los valores generales que cambiaron.
    Ante un error hace rollback y relanza la excepción.
    """
    configuracion = obtener_configuracion()

    # Se guardan los valores de antes para registrar qué cambió.
    anteriores = {
        "elementos_por_pagina": configuracion.elementos_por_pagina,
        "mantenimiento_activo": configuracion.mantenimiento_activo,
        "mensaje_mantenimiento": configuracion.mensaje_mantenimiento,
    }

    try:
        configuracion.elementos_por_pagina = datos["elementos_por_pagina"]
        configuracion.mantenimiento_activo = datos["mantenimiento_activo"]
        configuracion.mensaje_mantenimiento = datos["mensaje_mantenimiento"]
        _guardar_horarios(configuracion, datos)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("No se pudo actualizar la configuración (usuario %s)", usuario)
        raise

    # Solo los campos que cambiaron, como {campo: (antes, después)}.
    cambios = {
        campo: (anteriores[campo], datos[campo])
        for campo in anteriores
        if anteriores[campo] != datos[campo]
    }
    logger.info(
        "Configuración actualizada por %s. Cambios: %s", usuario, cambios or "ninguno"
    )
    logger.info("Horarios de comidas y de corte guardados por %s", usuario)
    return configuracion


def pedido_editable(fecha_pedido, ahora=None):
    """Dice si un pedido para ``fecha_pedido`` todavía se puede cargar, modificar o eliminar.

    Regla: la fecha tiene que ser futura y ``ahora`` tiene que ser antes del
    horario de corte del **día anterior** a la fecha. Por ejemplo, con corte
    20:00, un pedido para el jueves se acepta hasta el miércoles a las 19:59;
    a las 20:00 en punto ya no.

    - ``fecha_pedido``: un ``datetime.date``.
    - ``ahora``: un ``datetime``. Si no se pasa, se usa la hora actual de
      Argentina. Si trae zona horaria (por ejemplo UTC), se pasa a hora
      argentina antes de comparar. Si no trae zona, se asume que ya es
      hora argentina.

    Devuelve ``True`` o ``False``. La usa el módulo de Pedidos.
    """
    if ahora is None:
        ahora = datetime.now(ZONA_ARGENTINA)

    # Solo se convierte si trae zona: astimezone() sobre un datetime sin zona
    # lo tomaría como hora del servidor, que puede no ser la de Argentina.
    if ahora.tzinfo is not None:
        ahora = ahora.astimezone(ZONA_ARGENTINA)

    # Un pedido para hoy o para una fecha pasada nunca se puede tocar.
    if fecha_pedido <= ahora.date():
        return False

    # Si falta más de un día, todavía no llegó el corte.
    dia_anterior = fecha_pedido - timedelta(days=1)
    if ahora.date() < dia_anterior:
        return True

    # Es el día anterior: se puede solo hasta antes del horario de corte.
    return ahora.time() < obtener_configuracion().horario_corte
