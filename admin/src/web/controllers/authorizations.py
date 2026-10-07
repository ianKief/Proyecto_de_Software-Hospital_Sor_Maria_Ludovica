from datetime import date

from flask import Blueprint, jsonify, request, session

from src.core.pedidos.models import Pedido, SolicitudPedido, Autorizacion
from src.core.authorizations import (listar_autorizaciones as listar_autorizaciones_core, consultar_autorizacion as consultar_autorizacion_core, armar_detalle_pedido)
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

    fecha_desde_param = request.args.get("fecha_desde")
    fecha_hasta_param = request.args.get("fecha_hasta")

    try:
        fecha_desde = (
            date.fromisoformat(fecha_desde_param)
            if fecha_desde_param
            else None
        )
        fecha_hasta = (
            date.fromisoformat(fecha_hasta_param)
            if fecha_hasta_param
            else None
        )
        sector_id = request.args.get("sector_id")
        sector_id = int(sector_id) if sector_id else None

        pagina = request.args.get("pagina", 1, type=int)
        por_pagina = request.args.get("por_pagina", 25, type=int)

    except ValueError:
        return jsonify({
            "error": "Los parámetros no tienen un formato válido",
        }), 400

    try:
        pedidos, total = listar_autorizaciones_core(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=request.args.get("estado"),
            sector_id=sector_id,
            tipo_comida=request.args.get("tipo_comida"),
            tipo_menu=request.args.get("tipo_menu"),
            pagina=pagina,
            por_pagina=por_pagina,
        )

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    return jsonify({
        "pedidos": [
            armar_detalle_pedido(pedido)
            for pedido in pedidos
        ],
        "pagina": pagina,
        "por_pagina": min(por_pagina, 25),
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