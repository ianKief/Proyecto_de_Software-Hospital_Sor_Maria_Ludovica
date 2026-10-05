from flask import Blueprint, jsonify, request, session

from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.personnel.models import Personal
from src.core.pedidos.models import Pedido, SolicitudPedido
from src.core.quotas.models import Cupo
from src.core.users.models import User
from src.web.helpers.pedidos_validaciones import validar_pedido


pedidos_bp = Blueprint(
    "pedidos",
    __name__,
    url_prefix="/api/requests",
)


def _obtener_usuario_autenticado():
    """Obtiene el usuario autenticado a partir de la sesión."""

    user_id = session.get("user_id")

    if not user_id:
        return None

    return User.query.get(user_id)


def _obtener_tipos_comida():
    """Devuelve los tipos de comida indexados por nombre normalizado."""

    tipos = FoodType.query.all()

    return {
        tipo.nombre.lower(): tipo
        for tipo in tipos
    }


def _crear_solicitudes(
    pedido,
    detalle,
    sector_id,
):
    """Crea las solicitudes nominadas de un pedido."""

    tipos_comida = _obtener_tipos_comida()

    regular_actual = {}

    for nombre_comida, personas_ids in detalle.items():

        if not personas_ids:
            continue

        food_type = tipos_comida.get(nombre_comida)

        if not food_type:
            raise ValueError(
                f"No existe el tipo de comida '{nombre_comida}'"
            )

        cupo = Cupo.query.filter_by(
            sector_id=sector_id,
            tipo_comida_id=food_type.id,
        ).first()

        if not cupo:
            raise ValueError(
                f"No existe un cupo configurado para {nombre_comida}"
            )

        regular_actual[nombre_comida] = (
            SolicitudPedido.query
            .join(Pedido)
            .filter(
                Pedido.sector_id == sector_id,
                Pedido.fecha == pedido.fecha,
                SolicitudPedido.tipo_comida_id == food_type.id,
                SolicitudPedido.condicion == "regular",
            )
            .count()
        )

        for person_id in personas_ids:

            persona = Personal.query.get(person_id)

            if not persona:
                raise ValueError(
                    f"La persona {person_id} no existe"
                )

            if not persona.activo:
                raise ValueError(
                    f"La persona {person_id} se encuentra inactiva"
                )

            tipo_personal = persona.personnel_type

            if not tipo_personal:
                raise ValueError(
                    f"La persona {person_id} no tiene tipo de personal"
                )

            if tipo_personal.nombre == "Personal Fijo":
                if persona.sector_id != sector_id:
                    raise ValueError(
                        f"La persona {person_id} no pertenece "
                        "al sector del Jefe de Servicio"
                    )

            elif tipo_personal.nombre != "Residente":
                raise ValueError(
                    f"La persona {person_id} tiene un tipo de personal "
                    f"no contemplado: {tipo_personal.nombre}"
                )

            if regular_actual[nombre_comida] < cupo.cantidad:
                condicion = "regular"
                regular_actual[nombre_comida] += 1
            else:
                condicion = "excepcion"

            solicitud = SolicitudPedido(
                pedido=pedido,
                person_id=persona.id,
                tipo_comida_id=food_type.id,
                tipo_menu_id=persona.menu_type_id,
                condicion=condicion,
            )

            db.session.add(solicitud)


@pedidos_bp.route("", methods=["POST"])
def crear_pedido():
    """Crea un pedido y sus solicitudes nominadas."""

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

    # La semántica de cargas semanales/mensuales todavía no está
    # definida explícitamente en el TP. Por ahora persistimos pedidos
    # de una fecha puntual.
    if resultado["fecha_desde"] != resultado["fecha_hasta"]:
        return jsonify({
            "error": (
                "La creación de pedidos con rango de fechas "
                "todavía no está implementada"
            ),
        }), 400

    usuario = _obtener_usuario_autenticado()

    if not usuario:
        return jsonify({
            "error": "Usuario no autenticado",
        }), 401

    if not usuario.activo:
        return jsonify({
            "error": "El usuario se encuentra desactivado",
        }), 403

    if not usuario.sector_id:
        return jsonify({
            "error": "El Jefe de Servicio no tiene un sector asociado",
        }), 400

    sector = usuario.sector

    if not sector:
        return jsonify({
            "error": "El sector del usuario no existe",
        }), 400

    if not sector.activo:
        return jsonify({
            "error": "El sector del usuario se encuentra inactivo",
        }), 400

    fecha = resultado["fecha_desde"]

    pedido_existente = Pedido.query.filter_by(
        sector_id=sector.id,
        fecha=fecha,
    ).first()

    if pedido_existente:
        return jsonify({
            "error": "Ya existe un pedido para ese sector y fecha",
            "request_id": pedido_existente.id,
        }), 409

    pedido = Pedido(
        sector_id=sector.id,
        fecha=fecha,
        estado="confirmado",
        creado_por=usuario.id,
    )

    try:
        db.session.add(pedido)
        db.session.flush()

        _crear_solicitudes(
            pedido=pedido,
            detalle=resultado["detalle"],
            sector_id=sector.id,
        )

        db.session.commit()

    except ValueError as exc:
        db.session.rollback()

        return jsonify({
            "error": str(exc),
        }), 400

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "No se pudo crear el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido creado correctamente",
        "pedido": {
            "id": pedido.id,
            "sector_id": pedido.sector_id,
            "fecha": pedido.fecha.isoformat(),
            "estado": pedido.estado,
            "creado_por": pedido.creado_por,
            "solicitudes": [
                {
                    "id": solicitud.id,
                    "person_id": solicitud.person_id,
                    "tipo_comida_id": solicitud.tipo_comida_id,
                    "tipo_menu_id": solicitud.tipo_menu_id,
                    "condicion": solicitud.condicion,
                }
                for solicitud in pedido.solicitudes
            ],
        },
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