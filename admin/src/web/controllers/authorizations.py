from datetime import date

from flask import Blueprint, jsonify, request, session

from src.core.pedidos.models import Pedido, SolicitudPedido, Autorizacion
from src.core.authorizations import (
    listar_autorizaciones as listar_autorizaciones_core,
    consultar_autorizacion as consultar_autorizacion_core,
    armar_detalle_pedido,
    autorizar_pedido as autorizar_pedido_core,
    rechazar_pedido as rechazar_pedido_core,
)
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
    """Autoriza individualmente las solicitudes nominadas."""

    if not _es_servicio_alimentacion():
        return jsonify({
            "error": "No autorizado",
        }), 403

    usuario = _obtener_usuario_autenticado()

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    data = request.get_json(silent=True)

    if not data or not isinstance(data.get("solicitudes"), list):
        return jsonify({
            "error": "Debe indicar la lista de solicitudes a autorizar",
        }), 400

    try:
        pedido = autorizar_pedido_core(
            usuario=usuario,
            pedido_id=request_id,
            solicitudes_data=data["solicitudes"],
        )

    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404

    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 409

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    except Exception:
        return jsonify({
            "error": "No se pudo autorizar el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido autorizado correctamente",
        "pedido": armar_detalle_pedido(pedido),
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

    try:
        pedido = rechazar_pedido_core(
            usuario=usuario,
            pedido_id=request_id,
        )

    except LookupError as exc:
        return jsonify({
            "error": str(exc),
        }), 404

    except RuntimeError as exc:
        return jsonify({
            "error": str(exc),
        }), 409

    except Exception:
        return jsonify({
            "error": "No se pudo rechazar el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido rechazado correctamente",
        "request_id": pedido.id,
        "usuario_id": usuario.id,
    }), 200