"""Tests del validador de configuración."""
from src.web.helpers.configuracion_validaciones import validar_configuracion


def configuracion_base():
    """Devuelve datos válidos, como los manda el formulario de Ajustes."""
    return {
        "elementos_por_pagina": "10",
        "mantenimiento_activo": "on",
        "mensaje_mantenimiento": "  Volvemos a las 14 h  ",
    }


def test_configuracion_valida():
    data = configuracion_base()

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is True
    assert resultado == {
        "elementos_por_pagina": 10,
        "mantenimiento_activo": True,
        "mensaje_mantenimiento": "Volvemos a las 14 h",
    }


# Formulario: checkbox y campos propios

def test_checkbox_destildado_es_false():
    data = configuracion_base()
    del data["mantenimiento_activo"]

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is True
    assert resultado["mantenimiento_activo"] is False


def test_checkbox_tildado_es_true():
    data = configuracion_base()
    data["mantenimiento_activo"] = "on"

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is True
    assert resultado["mantenimiento_activo"] is True


def test_campos_del_formulario_se_ignoran():
    data = configuracion_base()
    data["csrf_token"] = "abc123"
    data["submit"] = "Guardar"

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is True
    assert "csrf_token" not in resultado
    assert "submit" not in resultado


def test_campo_extra_se_rechaza():
    data = configuracion_base()
    data["id"] = "1"

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is False
    assert resultado["error"] == "Se recibieron campos no permitidos"
    assert resultado["campos"] == ["id"]


# Elementos por página

def test_falta_elementos_por_pagina():
    data = configuracion_base()
    del data["elementos_por_pagina"]

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is False
    assert resultado["error"] == "Faltan campos obligatorios"


def test_elementos_por_pagina_fuera_de_rango():
    for valor in ["0", "26"]:
        data = configuracion_base()
        data["elementos_por_pagina"] = valor

        es_valido, resultado = validar_configuracion(data)

        assert es_valido is False
        assert resultado["campos"] == ["elementos_por_pagina"]


def test_elementos_por_pagina_no_entero():
    for valor in ["abc", "2.5", ""]:
        data = configuracion_base()
        data["elementos_por_pagina"] = valor

        es_valido, resultado = validar_configuracion(data)

        assert es_valido is False
        assert resultado["error"] == "Los elementos por página deben ser un número entero"


def test_elementos_por_pagina_bordes_validos():
    for valor in ["1", "25"]:
        data = configuracion_base()
        data["elementos_por_pagina"] = valor

        es_valido, resultado = validar_configuracion(data)

        assert es_valido is True
        assert resultado["elementos_por_pagina"] == int(valor)


# Mantenimiento y mensaje

def test_mantenimiento_activo_valor_invalido():
    data = configuracion_base()
    data["mantenimiento_activo"] = "si"

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is False
    assert resultado["campos"] == ["mantenimiento_activo"]


def test_mantenimiento_activo_sin_mensaje():
    for mensaje in ["", "   "]:
        data = configuracion_base()
        data["mensaje_mantenimiento"] = mensaje

        es_valido, resultado = validar_configuracion(data)

        assert es_valido is False
        assert resultado["error"] == "El mensaje es obligatorio si el mantenimiento está activo"


def test_mensaje_demasiado_largo():
    data = configuracion_base()
    data["mensaje_mantenimiento"] = "a" * 256

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is False
    assert resultado["campos"] == ["mensaje_mantenimiento"]


def test_mensaje_de_255_caracteres_es_valido():
    data = configuracion_base()
    data["mensaje_mantenimiento"] = "a" * 255

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is True


def test_mantenimiento_apagado_sin_mensaje_es_none():
    data = configuracion_base()
    del data["mantenimiento_activo"]
    data["mensaje_mantenimiento"] = ""

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is True
    assert resultado["mensaje_mantenimiento"] is None
