from collections import defaultdict
from datetime import timedelta

from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Pedido, SolicitudPedido


def _fecha_semana(fecha):
    """Obtiene el lunes de la semana correspondiente a una fecha."""
    return fecha - timedelta(days=fecha.weekday())


def _aplicar_filtros(query, filtros, usuario, es_jefe_servicio):
    """Aplica los filtros autorizados al listado de pedidos."""

    if filtros.get("fecha_desde"):
        query = query.filter(
            Pedido.fecha >= filtros["fecha_desde"]
        )

    if filtros.get("fecha_hasta"):
        query = query.filter(
            Pedido.fecha <= filtros["fecha_hasta"]
        )

    if es_jefe_servicio:
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
            raise ValueError("sector_id debe ser un entero")

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
            raise ValueError("Tipo de comida inexistente")

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
            raise ValueError("Tipo de menú inexistente")

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


def resumen_pedidos(filtros, usuario=None, es_jefe_servicio=False):
    """Obtiene el resumen de comidas pedidas."""

    query = _aplicar_filtros(
        Pedido.query,
        filtros,
        usuario,
        es_jefe_servicio,
    )

    pedidos = query.order_by(
        Pedido.fecha.asc(),
        Pedido.id.asc(),
    ).all()

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
        raise ValueError("Agrupamiento inválido")

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

    return pedidos, agrupamiento or "total", resultados


def resumen_autorizaciones(filtros):
    """Obtiene el resumen de comidas pedidas y autorizadas."""

    query = _aplicar_filtros(
        Pedido.query,
        filtros,
        None,
        False,
    )

    pedidos = query.order_by(
        Pedido.fecha.asc(),
        Pedido.id.asc(),
    ).all()

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
        raise ValueError("Agrupamiento inválido")

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

    return pedidos, agrupamiento or "total", dict(resultados)