from datetime import date

from flask import Blueprint, jsonify, request, session

from src.core.summaries import (
    resumen_pedidos as resumen_pedidos_core,
    resumen_autorizaciones as resumen_autorizaciones_core,
)

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

        pedidos, agrupamiento, resultados = resumen_pedidos_core(
            filtros=filtros,
            usuario=usuario,
            es_jefe_servicio=_es_jefe_servicio(),
        )

    except PermissionError as exc:
        return jsonify({
            "error": str(exc),
        }), 403

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    return jsonify({
        "agrupamiento": agrupamiento,
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

        pedidos, agrupamiento, resultados = resumen_autorizaciones_core(
            filtros=filtros,
        )

    except PermissionError as exc:
        return jsonify({
            "error": str(exc),
        }), 403

    except ValueError as exc:
        return jsonify({
            "error": str(exc),
        }), 400

    return jsonify({
        "agrupamiento": agrupamiento,
        "pedidos_considerados": len(pedidos),
        "resultados": resultados,
    }), 200