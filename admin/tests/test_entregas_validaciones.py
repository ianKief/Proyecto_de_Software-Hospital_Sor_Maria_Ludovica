"""Tests del validador de entregas."""
from src.web.helpers.entregas_validaciones import validar_entrega


def entrega_base():
    """Devuelve datos válidos, como los manda la pantalla del Comedor."""
    return {
        "personas": [3, 7],
        "tipo_comida_id": 2,
        "responsable_id": 3,
    }


def test_entrega_valida():
    data = entrega_base()

    es_valido, resultado = validar_entrega(data)

    assert es_valido is True
    assert resultado == {
        "personas": [3, 7],
        "tipo_comida_id": 2,
        "responsable_id": 3,
    }


# Estructura del cuerpo

def test_cuerpo_que_no_es_objeto():
    for data in [None, [], "texto"]:
        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["error"] == "El cuerpo debe ser un objeto JSON"


def test_campo_extra_se_rechaza():
    data = entrega_base()
    data["tipo_menu_id"] = 1

    es_valido, resultado = validar_entrega(data)

    assert es_valido is False
    assert resultado["error"] == "Se recibieron campos no permitidos"
    assert resultado["campos"] == ["tipo_menu_id"]


def test_falta_campo_obligatorio():
    for campo in ["personas", "tipo_comida_id", "responsable_id"]:
        data = entrega_base()
        del data[campo]

        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["error"] == "Faltan campos obligatorios"
        assert resultado["campos"] == [campo]


# Personas

def test_personas_no_es_lista():
    data = entrega_base()
    data["personas"] = 3

    es_valido, resultado = validar_entrega(data)

    assert es_valido is False
    assert resultado["error"] == "personas debe ser una lista"


def test_personas_vacia():
    data = entrega_base()
    data["personas"] = []

    es_valido, resultado = validar_entrega(data)

    assert es_valido is False
    assert resultado["error"] == "Debe incluir al menos una persona"


def test_persona_con_id_invalido():
    for valor in [0, -1, "3", 2.5, True, None]:
        data = entrega_base()
        data["personas"] = [3, valor]

        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["error"] == (
            "Los identificadores de personas deben ser enteros positivos"
        )


def test_personas_repetidas():
    data = entrega_base()
    data["personas"] = [3, 7, 3]

    es_valido, resultado = validar_entrega(data)

    assert es_valido is False
    assert resultado["error"] == "No se puede repetir una persona"


# Tipo de comida y responsable

def test_tipo_comida_invalido():
    for valor in [0, -2, "2", True, None]:
        data = entrega_base()
        data["tipo_comida_id"] = valor

        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["campos"] == ["tipo_comida_id"]


def test_responsable_invalido():
    for valor in [0, -3, "3", False, None]:
        data = entrega_base()
        data["responsable_id"] = valor

        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["campos"] == ["responsable_id"]
