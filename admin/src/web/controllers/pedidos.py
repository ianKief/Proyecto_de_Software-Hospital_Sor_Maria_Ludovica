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
        "datos": data,
    }), 201