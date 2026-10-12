"""Operaciones del módulo de Entregas."""
from src.core.db import db
from src.core.deliveries.models import EntregaDetalle
from src.core.deliveries.turnos import hoy
from src.core.pedidos.models import Autorizacion, Pedido, SolicitudPedido
from src.core.personnel.models import Personal
from src.core.sectors.models import Sector


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
