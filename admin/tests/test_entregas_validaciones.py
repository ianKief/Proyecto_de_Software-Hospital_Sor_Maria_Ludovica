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
        "responsable_dni": None,
        "responsable_nombre": None,
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
    for campo in ["personas", "tipo_comida_id"]:
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
    for valor in [0, -3, "3", False]:
        data = entrega_base()
        data["responsable_id"] = valor

        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["campos"] == ["responsable_id"]


# Responsable del retiro (EN1)

def entrega_de_tercero():
    """Devuelve una entrega de dos personas que retira un tercero."""
    return {
        "personas": [3, 7],
        "tipo_comida_id": 2,
        "responsable_dni": "30111222",
        "responsable_nombre": "Juan Pérez",
    }


def test_una_persona_sin_responsable_es_ella():
    data = {"personas": [3], "tipo_comida_id": 2}

    es_valido, resultado = validar_entrega(data)

    assert es_valido is True
    assert resultado["responsable_id"] == 3
    assert resultado["responsable_dni"] is None
    assert resultado["responsable_nombre"] is None


def test_responsable_en_null_cuenta_como_no_enviado():
    data = {
        "personas": [3],
        "tipo_comida_id": 2,
        "responsable_id": None,
        "responsable_dni": None,
        "responsable_nombre": None,
    }

    es_valido, resultado = validar_entrega(data)

    assert es_valido is True
    assert resultado["responsable_id"] == 3


def test_varias_personas_sin_responsable():
    data = entrega_base()
    del data["responsable_id"]

    es_valido, resultado = validar_entrega(data)

    assert es_valido is False
    assert resultado["error"] == (
        "El responsable es obligatorio cuando el retiro incluye más de una persona"
    )
    assert resultado["campos"] == ["responsable_id"]


def test_responsable_id_y_datos_de_tercero_a_la_vez():
    for campo, valor in [
        ("responsable_dni", "30111222"),
        ("responsable_nombre", "Juan Pérez"),
    ]:
        data = entrega_base()
        data[campo] = valor

        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["campos"] == [
            "responsable_id",
            "responsable_dni",
            "responsable_nombre",
        ]


def test_responsable_id_que_no_esta_en_la_entrega():
    data = entrega_base()
    data["responsable_id"] = 99

    es_valido, resultado = validar_entrega(data)

    assert es_valido is False
    assert resultado["campos"] == ["responsable_id"]
    assert "una de las personas de la entrega" in resultado["error"]


def test_tercero_valido():
    data = entrega_de_tercero()
    data["responsable_dni"] = " 30111222 "
    data["responsable_nombre"] = "  Juan Pérez  "

    es_valido, resultado = validar_entrega(data)

    assert es_valido is True
    assert resultado == {
        "personas": [3, 7],
        "tipo_comida_id": 2,
        "responsable_id": None,
        "responsable_dni": "30111222",
        "responsable_nombre": "Juan Pérez",
    }


def test_tercero_en_entrega_de_una_persona():
    data = entrega_de_tercero()
    data["personas"] = [3]

    es_valido, resultado = validar_entrega(data)

    assert es_valido is True
    assert resultado["responsable_id"] is None
    assert resultado["responsable_dni"] == "30111222"


def test_tercero_con_dni_invalido():
    for valor in ["123", "1234567890", "30.111.222", "30111a22", "", 30111222]:
        data = entrega_de_tercero()
        data["responsable_dni"] = valor

        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["campos"] == ["responsable_dni"]


def test_tercero_sin_dni_o_sin_nombre():
    for campo in ["responsable_dni", "responsable_nombre"]:
        data = entrega_de_tercero()
        del data[campo]

        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["error"] == "Para un tercero se necesitan el DNI y el nombre"
        assert resultado["campos"] == [campo]


def test_tercero_con_nombre_vacio_o_que_no_es_texto():
    for valor in ["", "   ", 5]:
        data = entrega_de_tercero()
        data["responsable_nombre"] = valor

        es_valido, resultado = validar_entrega(data)

        assert es_valido is False
        assert resultado["campos"] == ["responsable_nombre"]


def test_tercero_con_nombre_demasiado_largo():
    data = entrega_de_tercero()
    data["responsable_nombre"] = "a" * 256

    es_valido, resultado = validar_entrega(data)

    assert es_valido is False
    assert resultado["campos"] == ["responsable_nombre"]
