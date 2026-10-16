from datetime import date

from flask import Blueprint, jsonify, request, current_app

from src.core.db import db
from src.core.pedidos import (
    crear_pedidos,
    listar_pedidos as listar_pedidos_core,
    consultar_pedido as consultar_pedido_core,
    modificar_pedido as modificar_pedido_core,
    eliminar_pedido as eliminar_pedido_core,
)
from src.core.pedidos.models import Pedido, SolicitudPedido
from src.core.sectors.models import Sector
from src.web.helpers.pedidos_validaciones import validar_pedido
from src.web.helpers.api_auth import api_permission_required
from src.core.paginacion import paginar
from src.web.helpers.paginacion import validar_pagina, respuesta_paginada
pedidos_bp = Blueprint(
    "pedidos",
    __name__,
    url_prefix="/api/requests",
)

@pedidos_bp.route("", methods=["POST"])
@api_permission_required("request_new")
def crear_pedido(current_user):
    """Crea un pedido y sus solicitudes nominadas."""

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "El cuerpo de la solicitud es obligatorio",
        }), 400

    es_valido, resultado = validar_pedido(data)

    if not es_valido:
        return jsonify(resultado), 400

    usuario = current_user

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
@api_permission_required("request_index")
def listar_pedidos(current_user):
    """Lista los pedidos del sector del Jefe de Servicio autenticado."""

    usuario = current_user

    if not usuario:
        return jsonify({
            "error": "Usuario no autenticado",
        }), 401

    numero_pagina = validar_pagina(request.args.get("page"))

    if numero_pagina is None:
        return jsonify({
            "error": "El parámetro page no es válido",
        }), 400

    try:
        fecha_desde = request.args.get("fecha_desde")
        fecha_hasta = request.args.get("fecha_hasta")

        if fecha_desde:
            fecha_desde = date.fromisoformat(fecha_desde)

        if fecha_hasta:
            fecha_hasta = date.fromisoformat(fecha_hasta)

    except ValueError:
        return jsonify({
            "error": "Los parámetros de fecha no son válidos",
        }), 400

    try:
        consulta = listar_pedidos_core(
            usuario=usuario,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=request.args.get("estado"),
            tipo_comida=request.args.get("tipo_comida"),
            tipo_menu=request.args.get("tipo_menu"),
        )

        pagina = paginar(consulta, numero_pagina)

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    resultado = []

    for pedido in pagina.items:
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

        for solicitud in pedido.solicitudes:
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

    return jsonify(respuesta_paginada(pagina, resultado)), 200


@pedidos_bp.route("/<int:request_id>", methods=["GET"])
@api_permission_required("request_show")
def consultar_pedido(request_id, current_user):
    """Obtiene el detalle de un pedido."""

    usuario = current_user

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
        }), 400

    sector = Sector.query.get(pedido.sector_id)

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
@api_permission_required("request_update")
def modificar_pedido(request_id, current_user):
    """Modifica un pedido existente."""

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "El cuerpo de la solicitud es obligatorio",
        }), 400

    usuario = current_user

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    es_valido, resultado = validar_pedido(data)

    if not es_valido:
        return jsonify(resultado), 400

    try:
        pedido = modificar_pedido_core(
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
        current_app.logger.exception(
            "Error al modificar el pedido %s",
            request_id,
        )
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
@api_permission_required("request_destroy")
def eliminar_pedido(request_id, current_user):
    """Elimina un pedido existente."""

    usuario = current_user

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
        }), 400

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