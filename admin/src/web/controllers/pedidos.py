from flask import Blueprint, jsonify, request, session

from src.web.helpers.pedidos_validaciones import validar_pedido


pedidos_bp = Blueprint(
    "pedidos",
    __name__,
    url_prefix="/api/requests",
)


@pedidos_bp.route("", methods=["POST"])
def crear_pedido():
    """Crea un nuevo pedido de comidas."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "El cuerpo de la solicitud es obligatorio",
        }), 400

    es_valido, resultado = validar_pedido(data)

    if not es_valido:
        return jsonify(resultado), 400

    return jsonify({
        "mensaje": "Solicitud de creación de pedido recibida",
        "pedido": resultado,
    }), 201

@pedidos_bp.route("", methods=["GET"])
def listar_pedidos():
    """Lista los pedidos del sector del Jefe de Servicio autenticado."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    return jsonify({
        "pedidos": [],
        "pagina": 1,
        "por_pagina": 25,
        "total": 0,
    }), 200

@pedidos_bp.route("/<int:request_id>", methods=["GET"])
def consultar_pedido(request_id):
    """Obtiene el detalle de un pedido."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    return jsonify({
        "mensaje": "Consulta de pedido recibida",
        "request_id": request_id,
    }), 200

@pedidos_bp.route("/<int:request_id>", methods=["PUT"])
def modificar_pedido(request_id):
    """Modifica un pedido existente."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "El cuerpo de la solicitud es obligatorio",
        }), 400

    es_valido, resultado = validar_pedido(data)

    if not es_valido:
        return jsonify(resultado), 400

    return jsonify({
        "mensaje": "Solicitud de modificación de pedido recibida",
        "request_id": request_id,
        "pedido": resultado,
    }), 200


@pedidos_bp.route("/<int:request_id>", methods=["DELETE"])
def eliminar_pedido(request_id):
    """Elimina un pedido existente."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    return jsonify({
        "mensaje": "Solicitud de eliminación de pedido recibida",
        "request_id": request_id,
    }), 200