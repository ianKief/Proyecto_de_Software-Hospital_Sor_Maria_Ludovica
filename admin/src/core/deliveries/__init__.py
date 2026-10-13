"""Operaciones del módulo de Entregas."""
import logging

from sqlalchemy.exc import IntegrityError

from src.core.db import db
from src.core.deliveries.models import Entrega, EntregaDetalle
from src.core.deliveries.turnos import ahora, hoy, turno_actual
from src.core.food_types.models import FoodType
from src.core.pedidos.models import Autorizacion, Pedido, SolicitudPedido
from src.core.personnel.models import Personal
from src.core.sectors.models import Sector

logger = logging.getLogger(__name__)


def _consulta_autorizadas():
    """Consulta base de las solicitudes autorizadas.

    Una solicitud está autorizada si su pedido está en estado "autorizado"
    y su autorización individual tiene ``autorizada`` en True.
    Hace join con la persona para poder filtrar y ordenar por sus datos.
    """
    return (
        SolicitudPedido.query
        .join(SolicitudPedido.pedido)
        .join(SolicitudPedido.autorizacion)
        .join(SolicitudPedido.persona)
        .filter(Pedido.estado == "autorizado")
        .filter(Autorizacion.autorizada.is_(True))
    )


def buscar_comidas_autorizadas(
    fecha=None,
    dni=None,
    nombre=None,
    sector_id=None,
    tipo_comida_id=None,
):
    """Arma la consulta de comidas autorizadas con los filtros que vengan.

    - ``fecha``: fecha del pedido.
    - ``dni``: DNI exacto de la persona.
    - ``nombre``: texto parcial, sin distinguir mayúsculas, sobre "nombre apellido".
    - ``sector_id``: sector que hizo el pedido (no el sector actual de la persona).
    - ``tipo_comida_id``: tipo de comida de la solicitud.

    Las personas inactivas también aparecen. Devuelve la consulta sin
    ejecutar y con orden fijo, para pasarla a ``paginar()``.
    Que venga al menos un filtro lo controla el validador de la API.
    """
    consulta = _consulta_autorizadas()

    if fecha is not None:
        consulta = consulta.filter(Pedido.fecha == fecha)

    if dni:
        consulta = consulta.filter(Personal.dni == dni)

    if nombre:
        nombre_completo = Personal.nombre + " " + Personal.apellido
        consulta = consulta.filter(nombre_completo.ilike(f"%{nombre}%"))

    if sector_id is not None:
        consulta = consulta.filter(Pedido.sector_id == sector_id)

    if tipo_comida_id is not None:
        consulta = consulta.filter(
            SolicitudPedido.tipo_comida_id == tipo_comida_id
        )

    return consulta.order_by(
        Pedido.fecha,
        SolicitudPedido.tipo_comida_id,
        Personal.apellido,
        Personal.nombre,
        SolicitudPedido.id,
    )


def comidas_autorizadas_de(persona_id, fecha=None):
    """Devuelve la lista de solicitudes autorizadas de una persona en una fecha.

    Sin ``fecha`` usa la de hoy. Lanza ``LookupError`` si la persona no existe.
    """
    if db.session.get(Personal, persona_id) is None:
        raise LookupError("La persona no existe")

    if fecha is None:
        fecha = hoy()

    return (
        _consulta_autorizadas()
        .filter(SolicitudPedido.person_id == persona_id)
        .filter(Pedido.fecha == fecha)
        .order_by(SolicitudPedido.tipo_comida_id, SolicitudPedido.id)
        .all()
    )


def ya_entregada(persona_id, fecha, tipo_comida_id):
    """Indica si la persona ya retiró esa comida en esa fecha.

    Se controla por persona + fecha + comida, no por autorización: si la
    persona tiene dos autorizaciones (pedidas por dos sectores) y se entregó
    una, la otra también cuenta como entregada.
    """
    detalle = (
        EntregaDetalle.query
        .join(EntregaDetalle.autorizacion)
        .join(Autorizacion.solicitud)
        .join(SolicitudPedido.pedido)
        .filter(SolicitudPedido.person_id == persona_id)
        .filter(Pedido.fecha == fecha)
        .filter(SolicitudPedido.tipo_comida_id == tipo_comida_id)
        .first()
    )
    return detalle is not None


def datos_comida_autorizada(solicitud):
    """Arma el diccionario de una comida autorizada, listo para la API.

    El tipo de menú y la condición salen de la solicitud; el sector, del pedido.
    """
    pedido = solicitud.pedido
    persona = solicitud.persona
    # Pedido no tiene relación "sector" (issue #15): se busca por id.
    sector = db.session.get(Sector, pedido.sector_id)

    return {
        "autorizacion_id": solicitud.autorizacion.id,
        "fecha": pedido.fecha.isoformat(),
        "persona": {
            "id": persona.id,
            "dni": persona.dni,
            "nombre": persona.nombre,
            "apellido": persona.apellido,
            "activo": persona.activo,
        },
        "tipo_comida": {
            "id": solicitud.food_type.id,
            "nombre": solicitud.food_type.nombre,
        },
        "tipo_menu": {
            "id": solicitud.menu_type.id,
            "nombre": solicitud.menu_type.nombre,
        },
        "condicion": solicitud.condicion,
        "sector": {
            "id": sector.id,
            "nombre": sector.nombre,
        },
        "entregada": ya_entregada(
            persona.id,
            pedido.fecha,
            solicitud.tipo_comida_id,
        ),
    }


def _autorizacion_de_hoy(persona_id, fecha, tipo_comida_id):
    """Devuelve la autorización vigente de la persona para esa fecha y comida, o None.

    Si tiene dos (pedidas por dos sectores) devuelve la de menor id, así
    siempre se elige la misma y dos entregas simultáneas chocan en el UNIQUE.
    """
    solicitud = (
        _consulta_autorizadas()
        .filter(SolicitudPedido.person_id == persona_id)
        .filter(Pedido.fecha == fecha)
        .filter(SolicitudPedido.tipo_comida_id == tipo_comida_id)
        .order_by(Autorizacion.id)
        .first()
    )
    if solicitud is None:
        return None
    return solicitud.autorizacion


def registrar_entrega(datos, usuario_id):
    """Registra la entrega de una comida a una o varias personas y devuelve la Entrega.

    Recibe los datos ya validados por ``validar_entrega`` (``personas``,
    ``tipo_comida_id`` y ``responsable_id``) y el id del usuario del Comedor
    que la registra. La fecha y la hora las pone el servidor.

    Antes de crear nada controla todo; si algo falla no se guarda ninguna persona:
    - ``ValueError`` (400): comida o responsable inexistente, fuera del horario
      de esa comida, o alguna persona sin autorización para hoy.
    - ``RuntimeError`` (409): alguna persona ya retiró esa comida hoy.

    Las personas inactivas con la comida autorizada se entregan igual.
    """
    momento = ahora()
    fecha = momento.date()

    tipo_comida = db.session.get(FoodType, datos["tipo_comida_id"])
    if tipo_comida is None:
        raise ValueError("El tipo de comida no existe")

    if db.session.get(Personal, datos["responsable_id"]) is None:
        raise ValueError("El responsable del retiro no existe")

    if turno_actual(momento) != tipo_comida.nombre:
        raise ValueError(f"Fuera del horario de {tipo_comida.nombre}")

    # Se busca la autorización de cada persona; las que no tienen se juntan para avisar todas juntas.
    autorizaciones = []
    sin_autorizacion = []
    for persona_id in datos["personas"]:
        autorizacion = _autorizacion_de_hoy(persona_id, fecha, tipo_comida.id)
        if autorizacion is None:
            sin_autorizacion.append(persona_id)
        else:
            autorizaciones.append(autorizacion)

    if sin_autorizacion:
        raise ValueError(
            f"Sin autorización de {tipo_comida.nombre} para hoy: personas {sin_autorizacion}"
        )

    ya_retiraron = [
        persona_id
        for persona_id in datos["personas"]
        if ya_entregada(persona_id, fecha, tipo_comida.id)
    ]
    if ya_retiraron:
        raise RuntimeError(
            f"Ya retiraron {tipo_comida.nombre} hoy: personas {ya_retiraron}"
        )

    entrega = Entrega(
        usuario_id=usuario_id,
        responsable_id=datos["responsable_id"],
        tipo_comida_id=tipo_comida.id,
        detalles=[
            EntregaDetalle(autorizacion_id=autorizacion.id)
            for autorizacion in autorizaciones
        ],
    )

    try:
        db.session.add(entrega)
        db.session.commit()
    except IntegrityError:
        # Otra entrega de la misma autorización se guardó entre el control y el commit.
        db.session.rollback()
        logger.warning("Entrega duplicada rechazada (usuario %s)", usuario_id)
        raise RuntimeError("Alguna de las personas ya retiró esta comida")
    except Exception:
        db.session.rollback()
        logger.exception("No se pudo registrar la entrega (usuario %s)", usuario_id)
        raise

    logger.info(
        "Entrega %s registrada por el usuario %s: %s para %s personas",
        entrega.id,
        usuario_id,
        tipo_comida.nombre,
        len(autorizaciones),
    )
    return entrega
