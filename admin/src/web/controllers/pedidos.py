from datetime import date

from flask import Blueprint, jsonify, request, session

from src.core.db import db
from src.core.pedidos import (crear_pedidos, listar_pedidos, consultar_pedido as consultar_pedido_core, modificar_pedido, eliminar_pedido as eliminar_pedido_core,)
from src.core.pedidos.models import Pedido, SolicitudPedido
from src.core.sectors.models import Sector
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

    usuario = _obtener_usuario_autenticado()

    if not usuario:
        return jsonify({
            "error": "Usuario no autenticado",
        }), 401

    try:
        pedidos_creados, conflictos = crear_pedidos(
            usuario=usuario,
            resultado=resultado,
        )

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    except Exception:
        return jsonify({
            "error": "No se pudieron crear los pedidos",
        }), 500

    if not pedidos_creados:
        return jsonify({
            "error": "No se creó ningún pedido porque todas las fechas tenían conflictos.",
            "conflictos": conflictos,
        }), 409

    return jsonify({
        "mensaje": (
            "Pedidos creados correctamente"
            if not conflictos
            else "Se crearon los pedidos disponibles; algunas fechas tenían conflictos"
        ),
        "periodicidad": resultado["periodicidad"],
        "conflictos": conflictos,
        "pedidos": [
            {
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
            }
            for pedido in pedidos_creados
        ],
    }), 201


@pedidos_bp.route("", methods=["GET"])
def listar_pedidos():
    """Lista los pedidos del sector del Jefe de Servicio autenticado."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    usuario = _obtener_usuario_autenticado()

    if not usuario:
        return jsonify({
            "error": "Usuario no autenticado",
        }), 401

    try:
        fecha_desde = request.args.get("fecha_desde")
        fecha_hasta = request.args.get("fecha_hasta")

        if fecha_desde:
            fecha_desde = date.fromisoformat(fecha_desde)

        if fecha_hasta:
            fecha_hasta = date.fromisoformat(fecha_hasta)

        pagina = int(request.args.get("pagina", 1))
        por_pagina = int(request.args.get("por_pagina", 25))

    except ValueError:
        return jsonify({
            "error": "Los parámetros de fecha, página y paginación no son válidos",
        }), 400

    if pagina < 1:
        return jsonify({
            "error": "pagina debe ser mayor o igual a 1",
        }), 400

    if por_pagina < 1:
        return jsonify({
            "error": "por_pagina debe ser mayor o igual a 1",
        }), 400

    try:
        pedidos, total = listar_pedidos(
            usuario=usuario,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=request.args.get("estado"),
            tipo_comida=request.args.get("tipo_comida"),
            tipo_menu=request.args.get("tipo_menu"),
            pagina=pagina,
            por_pagina=por_pagina,
        )

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    resultado = []

    for pedido in pedidos:
        solicitudes = pedido.solicitudes

        totales_comida = {
            "desayuno": 0,
            "almuerzo": 0,
            "merienda": 0,
            "cena": 0,
        }

        totales_menu = {
            "General": 0,
            "Vegetariano": 0,
            "Celiaco": 0,
        }

        for solicitud in solicitudes:
            if solicitud.food_type:
                nombre_comida = solicitud.food_type.nombre.lower()

                if nombre_comida in totales_comida:
                    totales_comida[nombre_comida] += 1

            if solicitud.menu_type:
                nombre_menu = solicitud.menu_type.nombre

                if nombre_menu in totales_menu:
                    totales_menu[nombre_menu] += 1

        resultado.append({
            "id": pedido.id,
            "sector_id": pedido.sector_id,
            "fecha": pedido.fecha.isoformat(),
            "estado": pedido.estado,
            "creado_por": pedido.creado_por,
            "totales": {
                "por_comida": totales_comida,
                "por_menu": totales_menu,
            },
        })

    return jsonify({
        "pedidos": resultado,
        "pagina": pagina,
        "por_pagina": min(por_pagina, 25),
        "total": total,
    }), 200


@pedidos_bp.route("/<int:request_id>", methods=["GET"])
def consultar_pedido(request_id):
    """Obtiene el detalle de un pedido."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    usuario = _obtener_usuario_autenticado()

    if usuario is None:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    try:
        (
            pedido,
            solicitudes,
            totales_comida,
            totales_menu,
            detalle,
        ) = consultar_pedido_core(
            usuario=usuario,
            pedido_id=request_id,
        )

    except PermissionError as exc:
        return jsonify({
            "error": str(exc),
        }), 403

    except LookupError as exc:
        return jsonify({
            "error": str(exc),
        }), 404

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 401

    sector = pedido.sector

    return jsonify({
        "id": pedido.id,
        "fecha": pedido.fecha.isoformat(),
        "estado": pedido.estado,
        "sector": {
            "id": pedido.sector_id,
            "nombre": sector.nombre if sector else None,
        },
        "creado_por": pedido.creado_por,
        "totales": {
            "por_comida": totales_comida,
            "por_menu": totales_menu,
        },
        "solicitudes": detalle,
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

    usuario = _obtener_usuario_autenticado()

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    es_valido, resultado = validar_pedido(data)

    if not es_valido:
        return jsonify(resultado), 400

    try:
        pedido = modificar_pedido(
            usuario=usuario,
            pedido_id=request_id,
            resultado=resultado,
        )

    except PermissionError as exc:
        return jsonify({
            "error": str(exc),
        }), 403

    except LookupError as exc:
        return jsonify({
            "error": str(exc),
        }), 404

    except RuntimeError as exc:
        return jsonify({
            "error": str(exc),
        }), 409

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    except Exception:
        return jsonify({
            "error": "No se pudo modificar el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido modificado correctamente",
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
    }), 200


@pedidos_bp.route("/<int:request_id>", methods=["DELETE"])
def eliminar_pedido(request_id):
    """Elimina un pedido existente."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    usuario = _obtener_usuario_autenticado()

    if usuario is None:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    try:
        eliminar_pedido_core(
            usuario=usuario,
            pedido_id=request_id,
        )

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 401

    except PermissionError as exc:
        return jsonify({
            "error": str(exc),
        }), 403

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
            "error": "No se pudo eliminar el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido eliminado correctamente",
        "request_id": request_id,
    }), 200