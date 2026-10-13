from datetime import date

from src.web.helpers.pedidos_validaciones import validar_pedido


def pedido_base():
    return {
        "periodicidad": "diaria",
        "fecha_desde": "2026-10-05",
        "fecha_hasta": "2026-10-05",
        "detalle": {
            "desayuno": [1, 2],
            "almuerzo": [1],
            "merienda": [],
            "cena": [],
        },
    }


def test_pedido_valido():
    data = pedido_base()

    es_valido, resultado = validar_pedido(data)

    assert es_valido is True
    assert resultado["fecha_desde"] == date(2026, 10, 5)
    assert resultado["fecha_hasta"] == date(2026, 10, 5)
    assert resultado["detalle"]["desayuno"] == [1, 2]


def test_periodicidad_invalida():
    data = pedido_base()
    data["periodicidad"] = "anual"

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == "Periodicidad inválida"


def test_faltan_campos():
    data = pedido_base()
    del data["detalle"]

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert "campos" in resultado


def test_fecha_invalida():
    data = pedido_base()
    data["fecha_desde"] = "05-10-2026"

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == "Las fechas deben tener formato YYYY-MM-DD"


def test_rango_de_fechas_invalido():
    data = pedido_base()
    data["fecha_desde"] = "2026-10-10"
    data["fecha_hasta"] = "2026-10-05"

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == "fecha_hasta no puede ser anterior a fecha_desde"


def test_tipo_de_comida_invalido():
    data = pedido_base()
    data["detalle"]["colacion"] = [1]

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == "Se recibieron tipos de comida inválidos"


def test_persona_repetida():
    data = pedido_base()
    data["detalle"]["almuerzo"] = [1, 1]

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == "No se puede repetir una persona en almuerzo"


def test_no_hay_personas():
    data = pedido_base()
    data["detalle"] = {
        "desayuno": [],
        "almuerzo": [],
        "merienda": [],
        "cena": [],
    }

    es_valido, resultado = validar_pedido(data)

    assert es_valido is False
    assert resultado["error"] == (
        "Debe existir al menos una persona en alguna comida"
    )