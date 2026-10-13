from datetime import date

from flask import Blueprint, jsonify, request, session
from src.web.helpers.api_auth import api_permission_required
from src.core.pedidos.models import Pedido, SolicitudPedido, Autorizacion
from src.core.authorizations import (
    listar_autorizaciones as listar_autorizaciones_core,
    consultar_autorizacion as consultar_autorizacion_core,
    armar_detalle_pedido,
    autorizar_pedido as autorizar_pedido_core,
    rechazar_pedido as rechazar_pedido_core,
)
from src.core.paginacion import paginar
from src.web.helpers.paginacion import validar_pagina, respuesta_paginada
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


def _obtener_pedido(request_id):
    """Obtiene un pedido por su identificador."""
    return Pedido.query.get(request_id)


@authorizations_bp.route("", methods=["GET"])
@api_permission_required("authorization_index")
def listar_autorizaciones():
    """Lista pedidos para revisión del Servicio de Alimentación."""

    usuario = _obtener_usuario_autenticado()

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    numero_pagina = validar_pagina(request.args.get("page"))

    if numero_pagina is None:
        return jsonify({
            "error": "El parámetro page no es válido",
        }), 400

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

        sector_id_param = request.args.get("sector_id")
        sector_id = int(sector_id_param) if sector_id_param else None

    except ValueError:
        return jsonify({
            "error": "Los parámetros de fecha o sector no son válidos",
        }), 400

    try:
        consulta = listar_autorizaciones_core(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=request.args.get("estado"),
            sector_id=sector_id,
            tipo_comida=request.args.get("tipo_comida"),
            tipo_menu=request.args.get("tipo_menu"),
        )

        pagina = paginar(consulta, numero_pagina)

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    pedidos = [
        armar_detalle_pedido(pedido)
        for pedido in pagina.items
    ]

    return jsonify(respuesta_paginada(pagina, pedidos)), 200


@authorizations_bp.route("/<int:request_id>", methods=["GET"])
@api_permission_required("authorization_show")
def consultar_autorizacion(request_id):
    """Obtiene el detalle de un pedido para autorizarlo."""

    pedido = _obtener_pedido(request_id)

    if pedido is None:
        return jsonify({
            "error": "Pedido no encontrado",
        }), 404

    return jsonify(armar_detalle_pedido(pedido)), 200


@authorizations_bp.route("/<int:request_id>", methods=["PUT"])
@api_permission_required("authorization_update")
def autorizar_pedido(request_id):
    """Autoriza individualmente las solicitudes nominadas."""

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
@api_permission_required("authorization_update")
def rechazar_pedido(request_id):
    """Rechaza un pedido."""

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