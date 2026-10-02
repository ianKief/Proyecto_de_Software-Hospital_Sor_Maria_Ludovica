from datetime import date

from src.web.helpers.pedidos_validaciones import validar_pedido


def test_pedido_valido():
    data = {
        "periodicidad": "diaria",
        "fecha_desde": "2026-10-05",
        "fecha_hasta": "2026-10-05",
        "personas": [1, 2],
    }

    es_valido, resultado = validar_pedido(data)

    assert es_valido is True
    assert resultado["fecha_desde"] == date(2026, 10, 5)
    assert resultado["fecha_hasta"] == date(2026, 10, 5)


def test_periodicidad_invalida():
    data = {
        "periodicidad": "anual",
        "fecha_desde": "2026-10-05",
        "fecha_hasta": "2026-10-05",
        "personas": [1],
    }

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == "Periodicidad inválida"


def test_faltan_campos():
    data = {
        "periodicidad": "diaria",
        "fecha_desde": "2026-10-05",
    }

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert "campos" in resultado


def test_fecha_invalida():
    data = {
        "periodicidad": "diaria",
        "fecha_desde": "05-10-2026",
        "fecha_hasta": "2026-10-05",
        "personas": [1],
    }

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == "Las fechas deben tener formato YYYY-MM-DD"


def test_rango_de_fechas_invalido():
    data = {
        "periodicidad": "diaria",
        "fecha_desde": "2026-10-10",
        "fecha_hasta": "2026-10-05",
        "personas": [1],
    }

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == "fecha_hasta no puede ser anterior a fecha_desde"


def test_personas_debe_ser_lista():
    data = {
        "periodicidad": "diaria",
        "fecha_desde": "2026-10-05",
        "fecha_hasta": "2026-10-05",
        "personas": 1,
    }

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == "personas debe ser una lista no vacía"