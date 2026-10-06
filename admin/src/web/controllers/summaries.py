from collections import defaultdict
from datetime import date

from flask import Blueprint, jsonify, request, session

from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Pedido, SolicitudPedido


summaries_bp = Blueprint(
    "summaries",
    __name__,
    url_prefix="/api/summaries",
)


def _es_servicio_alimentacion():
    """Verifica si el usuario autenticado tiene rol de Servicio de Alimentación."""
    return session.get("role") == "Servicio de Alimentación"


def _es_jefe_servicio():
    """Verifica si el usuario autenticado tiene rol de Jefe de Servicio."""
    return session.get("role") == "Jefe de Servicio"


def _fecha_semana(fecha):
    """Obtiene el lunes de la semana correspondiente a una fecha."""
    return fecha - __import__("datetime").timedelta(days=fecha.weekday())


def _obtener_filtros():
    """Obtiene y valida los filtros utilizados por los resúmenes."""

    filtros = {}

    fecha_desde_param = request.args.get("fecha_desde")
    fecha_hasta_param = request.args.get("fecha_hasta")

    if fecha_desde_param:
        try:
            filtros["fecha_desde"] = date.fromisoformat(fecha_desde_param)
        except ValueError:
            raise ValueError(
                "fecha_desde debe tener formato YYYY-MM-DD"
            )

    if fecha_hasta_param:
        try:
            filtros["fecha_hasta"] = date.fromisoformat(fecha_hasta_param)
        except ValueError:
            raise ValueError(
                "fecha_hasta debe tener formato YYYY-MM-DD"
            )

    if (
        filtros.get("fecha_desde")
        and filtros.get("fecha_hasta")
        and filtros["fecha_desde"] > filtros["fecha_hasta"]
    ):
        raise ValueError(
            "fecha_hasta no puede ser anterior a fecha_desde"
        )

    filtros["sector_id"] = request.args.get("sector_id")
    filtros["tipo_comida"] = request.args.get("tipo_comida")
    filtros["tipo_menu"] = request.args.get("tipo_menu")
    filtros["estado"] = request.args.get("estado")
    filtros["agrupamiento"] = request.args.get("agrupamiento")

    return filtros


def _aplicar_filtros(query, filtros, usuario):
    """Aplica los filtros autorizados al listado de pedidos."""

    if filtros.get("fecha_desde"):
        query = query.filter(
            Pedido.fecha >= filtros["fecha_desde"]
        )

    if filtros.get("fecha_hasta"):
        query = query.filter(
            Pedido.fecha <= filtros["fecha_hasta"]
        )

    if _es_jefe_servicio():
        if usuario is None or usuario.sector_id is None:
            raise PermissionError(
                "El Jefe de Servicio no tiene un sector asignado"
            )

        query = query.filter(
            Pedido.sector_id == usuario.sector_id
        )

    elif filtros.get("sector_id"):
        try:
            sector_id = int(filtros["sector_id"])
        except ValueError:
            raise ValueError(
                "sector_id debe ser un entero"
            )

        query = query.filter(
            Pedido.sector_id == sector_id
        )

    if filtros.get("estado"):
        estados_validos = {
            "confirmado",
            "autorizado",
            "rechazado",
        }

        if filtros["estado"] not in estados_validos:
            raise ValueError("Estado inválido")

        query = query.filter(
            Pedido.estado == filtros["estado"]
        )

    if filtros.get("tipo_comida"):
        food_type = FoodType.query.filter(
            db.func.lower(FoodType.nombre)
            == filtros["tipo_comida"].lower()
        ).first()

        if not food_type:
            raise ValueError(
                "Tipo de comida inexistente"
            )

        query = query.filter(
            Pedido.solicitudes.any(
                SolicitudPedido.tipo_comida_id == food_type.id
            )
        )

    if filtros.get("tipo_menu"):
        menu_type = MenuType.query.filter(
            db.func.lower(MenuType.nombre)
            == filtros["tipo_menu"].lower()
        ).first()

        if not menu_type:
            raise ValueError(
                "Tipo de menú inexistente"
            )

        query = query.filter(
            Pedido.solicitudes.any(
                SolicitudPedido.tipo_menu_id == menu_type.id
            )
        )

    return query


def _clave_agrupamiento(pedido, solicitud, agrupamiento):
    """Determina la clave de agrupamiento del resumen."""

    if agrupamiento == "dia":
        return pedido.fecha.isoformat()

    if agrupamiento == "semana":
        return _fecha_semana(pedido.fecha).isoformat()

    if agrupamiento == "mes":
        return pedido.fecha.strftime("%Y-%m")

    if agrupamiento == "sector":
        return str(pedido.sector_id)

    if agrupamiento == "comida":
        return solicitud.food_type.nombre

    if agrupamiento == "menu":
        return solicitud.menu_type.nombre

    return "total"


@summaries_bp.route("/requests", methods=["GET"])
def resumen_pedidos():
    """Obtiene el resumen de comidas pedidas."""

    if not (_es_servicio_alimentacion() or _es_jefe_servicio()):
        return jsonify({
            "error": "No autorizado",
        }), 403

    try:
        filtros = _obtener_filtros()

        usuario = None

        if _es_jefe_servicio():
            from src.core.users.models import User

            user_id = session.get("user_id")

            if not user_id:
                return jsonify({
                    "error": "Usuario no autenticado",
                }), 401

            usuario = User.query.get(user_id)

        query = _aplicar_filtros(
            Pedido.query,
            filtros,
            usuario,
        )

        pedidos = query.order_by(
            Pedido.fecha.asc(),
            Pedido.id.asc(),
        ).all()

    except PermissionError as exc:
        return jsonify({
            "error": str(exc),
        }), 403

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    agrupamiento = filtros.get("agrupamiento")

    agrupamientos_validos = {
        "dia",
        "semana",
        "mes",
        "sector",
        "comida",
        "menu",
    }

    if agrupamiento and agrupamiento not in agrupamientos_validos:
        return jsonify({
            "error": "Agrupamiento inválido",
            "valores_permitidos": sorted(agrupamientos_validos),
        }), 400

    resultados = defaultdict(int)

    for pedido in pedidos:
        for solicitud in pedido.solicitudes:
            clave = _clave_agrupamiento(
                pedido,
                solicitud,
                agrupamiento,
            )

            resultados[clave] += 1

    if agrupamiento == "sector":
        resultados = {
            clave: {
                "sector_id": int(clave),
                "cantidad": cantidad,
            }
            for clave, cantidad in resultados.items()
        }
    else:
        resultados = {
            clave: {
                "cantidad": cantidad,
            }
            for clave, cantidad in resultados.items()
        }

    return jsonify({
        "agrupamiento": agrupamiento or "total",
        "pedidos_considerados": len(pedidos),
        "resultados": resultados,
    }), 200

@summaries_bp.route("/authorizations", methods=["GET"])
def resumen_autorizaciones():
    """Obtiene el resumen de comidas pedidas y autorizadas."""

    if not _es_servicio_alimentacion():
        return jsonify({
            "error": "No autorizado",
        }), 403

    try:
        filtros = _obtener_filtros()

        query = _aplicar_filtros(
            Pedido.query,
            filtros,
            None,
        )

        pedidos = query.order_by(
            Pedido.fecha.asc(),
            Pedido.id.asc(),
        ).all()

    except PermissionError as exc:
        return jsonify({
            "error": str(exc),
        }), 403

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    agrupamiento = filtros.get("agrupamiento")

    agrupamientos_validos = {
        "dia",
        "semana",
        "mes",
        "sector",
        "comida",
        "menu",
    }

    if agrupamiento and agrupamiento not in agrupamientos_validos:
        return jsonify({
            "error": "Agrupamiento inválido",
            "valores_permitidos": sorted(agrupamientos_validos),
        }), 400

    resultados = defaultdict(
        lambda: {
            "pedidas": 0,
            "autorizadas": 0,
            "diferencia": 0,
        }
    )

    for pedido in pedidos:
        for solicitud in pedido.solicitudes:
            clave = _clave_agrupamiento(
                pedido,
                solicitud,
                agrupamiento,
            )

            resultados[clave]["pedidas"] += 1

            if (
                solicitud.autorizacion is not None
                and solicitud.autorizacion.autorizada
            ):
                resultados[clave]["autorizadas"] += 1

    for datos in resultados.values():
        datos["diferencia"] = (
            datos["pedidas"] - datos["autorizadas"]
        )

    return jsonify({
        "agrupamiento": agrupamiento or "total",
        "pedidos_considerados": len(pedidos),
        "resultados": dict(resultados),
    }), 200