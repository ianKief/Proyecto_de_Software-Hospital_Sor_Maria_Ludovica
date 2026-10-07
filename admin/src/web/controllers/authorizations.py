from datetime import date

from flask import Blueprint, jsonify, request, session

from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Pedido, SolicitudPedido, Autorizacion
from src.core.sectors.models import Sector
from src.core.users.models import User


authorizations_bp = Blueprint(
    "authorizations",
    __name__,
    url_prefix="/api/authorizations",
)


def _obtener_usuario_autenticado():
    """Obtiene el usuario autenticado a partir de la sesión."""
    user_id = session.get("user_id")

    if not user_id:
        return None

    return User.query.get(user_id)


def _es_servicio_alimentacion():
    """Verifica si el usuario actual pertenece al Servicio de Alimentación."""
    return session.get("role") == "Servicio de Alimentación"


def _obtener_pedido(request_id):
    """Obtiene un pedido por su identificador."""
    return Pedido.query.get(request_id)


def _armar_detalle_pedido(pedido):
    """Construye el detalle del pedido con cantidades pedidas y autorizadas."""

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


@authorizations_bp.route("", methods=["GET"])
def listar_autorizaciones():
    """Lista pedidos para revisión del Servicio de Alimentación."""

    if not _es_servicio_alimentacion():
        return jsonify({
            "error": "No autorizado",
        }), 403

    usuario = _obtener_usuario_autenticado()

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    query = Pedido.query

    fecha_desde_param = request.args.get("fecha_desde")
    fecha_hasta_param = request.args.get("fecha_hasta")
    estado = request.args.get("estado")
    sector_id = request.args.get("sector_id")
    tipo_comida = request.args.get("tipo_comida")
    tipo_menu = request.args.get("tipo_menu")

    if fecha_desde_param:
        try:
            fecha_desde = date.fromisoformat(fecha_desde_param)
        except ValueError:
            return jsonify({
                "error": "fecha_desde debe tener formato YYYY-MM-DD",
            }), 400

        query = query.filter(Pedido.fecha >= fecha_desde)

    if fecha_hasta_param:
        try:
            fecha_hasta = date.fromisoformat(fecha_hasta_param)
        except ValueError:
            return jsonify({
                "error": "fecha_hasta debe tener formato YYYY-MM-DD",
            }), 400

        query = query.filter(Pedido.fecha <= fecha_hasta)

    if (
        fecha_desde_param
        and fecha_hasta_param
        and fecha_desde > fecha_hasta
    ):
        return jsonify({
            "error": "fecha_hasta no puede ser anterior a fecha_desde",
        }), 400

    estados_validos = {
        "confirmado",
        "autorizado",
        "rechazado",
    }

    if estado:
        if estado not in estados_validos:
            return jsonify({
                "error": "Estado inválido",
                "valores_permitidos": sorted(estados_validos),
            }), 400

        query = query.filter(Pedido.estado == estado)
    else:
        query = query.filter(
            Pedido.estado.in_(["confirmado", "autorizado"])
        )

    if sector_id:
        try:
            sector_id = int(sector_id)
        except ValueError:
            return jsonify({
                "error": "sector_id debe ser un entero",
            }), 400

        query = query.filter(Pedido.sector_id == sector_id)

    if tipo_comida:
        food_type = FoodType.query.filter(
            db.func.lower(FoodType.nombre) == tipo_comida.lower()
        ).first()

        if not food_type:
            return jsonify({
                "error": "Tipo de comida inexistente",
            }), 400

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
            return jsonify({
                "error": "Tipo de menú inexistente",
            }), 400

        query = query.filter(
            Pedido.solicitudes.any(
                SolicitudPedido.tipo_menu_id == menu_type.id
            )
        )

    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = request.args.get("por_pagina", 25, type=int)

    if pagina < 1 or por_pagina < 1:
        return jsonify({
            "error": "pagina y por_pagina deben ser valores positivos",
        }), 400

    por_pagina = min(por_pagina, 25)

    total = query.count()

    pedidos = (
        query
        .order_by(Pedido.fecha.desc(), Pedido.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    return jsonify({
        "pedidos": [
            _armar_detalle_pedido(pedido)
            for pedido in pedidos
        ],
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": total,
    }), 200


@authorizations_bp.route("/<int:request_id>", methods=["GET"])
def consultar_autorizacion(request_id):
    """Obtiene el detalle de un pedido para autorizarlo."""

    if not _es_servicio_alimentacion():
        return jsonify({
            "error": "No autorizado",
        }), 403

    pedido = _obtener_pedido(request_id)

    if pedido is None:
        return jsonify({
            "error": "Pedido no encontrado",
        }), 404

    return jsonify(_armar_detalle_pedido(pedido)), 200


@authorizations_bp.route("/<int:request_id>", methods=["PUT"])
def autorizar_pedido(request_id):
    """Autoriza individualmente las solicitudes nominadas de un pedido."""

    if not _es_servicio_alimentacion():
        return jsonify({
            "error": "No autorizado",
        }), 403

    usuario = _obtener_usuario_autenticado()

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    pedido = _obtener_pedido(request_id)

    if pedido is None:
        return jsonify({
            "error": "Pedido no encontrado",
        }), 404

    if pedido.estado in {"autorizado", "rechazado"}:
        return jsonify({
            "error": "El pedido ya fue autorizado o rechazado",
        }), 409

    data = request.get_json(silent=True)

    if not data or not isinstance(data.get("solicitudes"), list):
        return jsonify({
            "error": "Debe indicar la lista de solicitudes a autorizar",
        }), 400

    solicitudes = {
        solicitud.id: solicitud
        for solicitud in SolicitudPedido.query.filter_by(
            pedido_id=pedido.id
        ).all()
    }

    autorizaciones = data["solicitudes"]

    try:
        for item in autorizaciones:
            solicitud_id = item.get("solicitud_id")
            autorizada = item.get("autorizada")

            if not isinstance(solicitud_id, int):
                return jsonify({
                    "error": "solicitud_id debe ser un entero",
                }), 400

            if not isinstance(autorizada, bool):
                return jsonify({
                    "error": "autorizada debe ser booleano",
                }), 400

            solicitud = solicitudes.get(solicitud_id)

            if solicitud is None:
                return jsonify({
                    "error": (
                        f"La solicitud {solicitud_id} "
                        "no pertenece al pedido"
                    ),
                }), 400

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

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "No se pudo autorizar el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido autorizado correctamente",
        "pedido": _armar_detalle_pedido(pedido),
    }), 200


@authorizations_bp.route(
    "/<int:request_id>/reject",
    methods=["POST"]
)
def rechazar_pedido(request_id):
    """Rechaza un pedido."""

    if not _es_servicio_alimentacion():
        return jsonify({
            "error": "No autorizado",
        }), 403

    usuario = _obtener_usuario_autenticado()

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    pedido = _obtener_pedido(request_id)

    if pedido is None:
        return jsonify({
            "error": "Pedido no encontrado",
        }), 404

    if pedido.estado == "autorizado":
        return jsonify({
            "error": "El pedido ya fue autorizado",
        }), 409

    if pedido.estado == "rechazado":
        return jsonify({
            "error": "El pedido ya fue rechazado",
        }), 409

    pedido.estado = "rechazado"

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "No se pudo rechazar el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido rechazado correctamente",
        "request_id": pedido.id,
        "usuario_id": usuario.id,
    }), 200