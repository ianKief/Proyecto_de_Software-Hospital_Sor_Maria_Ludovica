from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Pedido, SolicitudPedido


def armar_detalle_pedido(pedido):
    """Construye el detalle de un pedido."""

    solicitudes = (
        SolicitudPedido.query
        .filter_by(pedido_id=pedido.id)
        .all()
    )

    totales_comida = {}
    totales_menu = {}
    detalle = []

    for solicitud in solicitudes:
        nombre_comida = solicitud.food_type.nombre
        nombre_menu = solicitud.menu_type.nombre

        autorizada = (
            solicitud.autorizacion is not None
            and solicitud.autorizacion.autorizada
        )

        if nombre_comida not in totales_comida:
            totales_comida[nombre_comida] = {
                "solicitadas": 0,
                "autorizadas": 0,
            }

        if nombre_menu not in totales_menu:
            totales_menu[nombre_menu] = {
                "solicitadas": 0,
                "autorizadas": 0,
            }

        totales_comida[nombre_comida]["solicitadas"] += 1
        totales_menu[nombre_menu]["solicitadas"] += 1

        if autorizada:
            totales_comida[nombre_comida]["autorizadas"] += 1
            totales_menu[nombre_menu]["autorizadas"] += 1

        detalle.append({
            "solicitud_id": solicitud.id,
            "persona": {
                "id": solicitud.persona.id,
                "dni": solicitud.persona.dni,
                "nombre": solicitud.persona.nombre,
                "apellido": solicitud.persona.apellido,
            },
            "tipo_comida": {
                "id": solicitud.tipo_comida_id,
                "nombre": solicitud.food_type.nombre,
            },
            "tipo_menu": {
                "id": solicitud.tipo_menu_id,
                "nombre": solicitud.menu_type.nombre,
            },
            "condicion": solicitud.condicion,
            "autorizada": (
                solicitud.autorizacion.autorizada
                if solicitud.autorizacion is not None
                else None
            ),
        })

    return {
        "id": pedido.id,
        "fecha": pedido.fecha.isoformat(),
        "sector": {
            "id": pedido.sector_id,
        },
        "estado": pedido.estado,
        "creado_por": pedido.creado_por,
        "totales": {
            "por_comida": totales_comida,
            "por_menu": totales_menu,
        },
        "solicitudes": detalle,
    }


def listar_autorizaciones(
    fecha_desde=None,
    fecha_hasta=None,
    estado=None,
    sector_id=None,
    tipo_comida=None,
    tipo_menu=None,
    pagina=1,
    por_pagina=25,
):
    """Lista pedidos para revisión del Servicio de Alimentación."""

    query = Pedido.query

    if fecha_desde:
        query = query.filter(Pedido.fecha >= fecha_desde)

    if fecha_hasta:
        query = query.filter(Pedido.fecha <= fecha_hasta)

    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ValueError(
            "fecha_hasta no puede ser anterior a fecha_desde"
        )

    estados_validos = {
        "confirmado",
        "autorizado",
        "rechazado",
    }

    if estado:
        if estado not in estados_validos:
            raise ValueError("Estado inválido")

        query = query.filter(Pedido.estado == estado)
    else:
        query = query.filter(
            Pedido.estado.in_(["confirmado", "autorizado"])
        )

    if sector_id is not None:
        query = query.filter(Pedido.sector_id == sector_id)

    if tipo_comida:
        food_type = FoodType.query.filter(
            db.func.lower(FoodType.nombre) == tipo_comida.lower()
        ).first()

        if not food_type:
            raise ValueError("Tipo de comida inexistente")

        query = query.filter(
            Pedido.solicitudes.any(
                SolicitudPedido.tipo_comida_id == food_type.id
            )
        )

    if tipo_menu:
        menu_type = MenuType.query.filter(
            db.func.lower(MenuType.nombre) == tipo_menu.lower()
        ).first()

        if not menu_type:
            raise ValueError("Tipo de menú inexistente")

        query = query.filter(
            Pedido.solicitudes.any(
                SolicitudPedido.tipo_menu_id == menu_type.id
            )
        )

    if pagina < 1 or por_pagina < 1:
        raise ValueError(
            "pagina y por_pagina deben ser valores positivos"
        )

    por_pagina = min(por_pagina, 25)

    total = query.count()

    pedidos = (
        query
        .order_by(Pedido.fecha.desc(), Pedido.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    return pedidos, total


def consultar_autorizacion(request_id):
    """Obtiene el detalle de un pedido."""

    pedido = Pedido.query.get(request_id)

    if pedido is None:
        raise LookupError("Pedido no encontrado")

    return armar_detalle_pedido(pedido)

def autorizar_pedido(usuario, pedido_id, solicitudes_data):
    """Autoriza las solicitudes nominadas de un pedido."""
    pedido = Pedido.query.get(pedido_id)

    if pedido is None:
        raise LookupError("Pedido no encontrado")

    if pedido.estado in {"autorizado", "rechazado"}:
        raise RuntimeError(
            "El pedido ya fue autorizado o rechazado"
        )

    solicitudes = {
        solicitud.id: solicitud
        for solicitud in SolicitudPedido.query.filter_by(
            pedido_id=pedido.id
        ).all()
    }

    try:
        for item in solicitudes_data:
            solicitud_id = item.get("solicitud_id")
            autorizada = item.get("autorizada")

            if not isinstance(solicitud_id, int):
                raise ValueError(
                    "solicitud_id debe ser un entero"
                )

            if not isinstance(autorizada, bool):
                raise ValueError(
                    "autorizada debe ser booleano"
                )

            solicitud = solicitudes.get(solicitud_id)

            if solicitud is None:
                raise ValueError(
                    f"La solicitud {solicitud_id} "
                    "no pertenece al pedido"
                )

            if solicitud.autorizacion is None:
                solicitud.autorizacion = Autorizacion(
                    solicitud_id=solicitud.id,
                    autorizada=autorizada,
                    usuario_id=usuario.id,
                )
            else:
                solicitud.autorizacion.autorizada = autorizada
                solicitud.autorizacion.usuario_id = usuario.id

        db.session.flush()

        for solicitud in solicitudes.values():
            if solicitud.autorizacion is None:
                solicitud.autorizacion = Autorizacion(
                    solicitud_id=solicitud.id,
                    autorizada=False,
                    usuario_id=usuario.id,
                )

        pedido.estado = "autorizado"
        db.session.commit()

        return pedido

    except Exception:
        db.session.rollback()
        raise

def rechazar_pedido(usuario, pedido_id):
    """Rechaza un pedido."""
    pedido = Pedido.query.get(pedido_id)

    if pedido is None:
        raise LookupError("Pedido no encontrado")

    if pedido.estado == "autorizado":
        raise RuntimeError("El pedido ya fue autorizado")

    if pedido.estado == "rechazado":
        raise RuntimeError("El pedido ya fue rechazado")

    try:
        pedido.estado = "rechazado"
        db.session.commit()
        return pedido

    except Exception:
        db.session.rollback()
        raise