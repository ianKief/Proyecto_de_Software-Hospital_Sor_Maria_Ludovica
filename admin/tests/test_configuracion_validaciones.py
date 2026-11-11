"""Tests del validador de configuración."""
from datetime import time

from src.web.helpers.configuracion_validaciones import validar_configuracion


def configuracion_base():
    """Devuelve datos válidos, como los manda el formulario de Ajustes."""
    return {
        "elementos_por_pagina": "10",
        "mantenimiento_activo": "on",
        "mensaje_mantenimiento": "  Volvemos a las 14 h  ",
        "desayuno_inicio": "06:00",
        "desayuno_fin": "10:00",
        "almuerzo_inicio": "11:30",
        "almuerzo_fin": "15:00",
        "merienda_inicio": "16:00",
        "merienda_fin": "18:30",
        "cena_inicio": "20:00",
        "cena_fin": "23:00",
        "horario_corte": "20:00",
    }


def test_configuracion_valida():
    data = configuracion_base()

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is True
    assert resultado == {
        "elementos_por_pagina": 10,
        "mantenimiento_activo": True,
        "mensaje_mantenimiento": "Volvemos a las 14 h",
        "desayuno_inicio": time(6, 0),
        "desayuno_fin": time(10, 0),
        "almuerzo_inicio": time(11, 30),
        "almuerzo_fin": time(15, 0),
        "merienda_inicio": time(16, 0),
        "merienda_fin": time(18, 30),
        "cena_inicio": time(20, 0),
        "cena_fin": time(23, 0),
        "horario_corte": time(20, 0),
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


# Horarios de comidas y de corte

def test_falta_un_horario():
    data = configuracion_base()
    del data["merienda_fin"]

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is False
    assert resultado["error"] == "Faltan campos obligatorios"
    assert resultado["campos"] == ["merienda_fin"]


def test_horario_con_formato_invalido():
    for valor in ["25:00", "abc", ""]:
        data = configuracion_base()
        data["merienda_inicio"] = valor

        es_valido, resultado = validar_configuracion(data)

        assert es_valido is False
        assert resultado["error"] == "El inicio de la merienda debe tener el formato HH:MM"
        assert resultado["campos"] == ["merienda_inicio"]


def test_inicio_igual_o_posterior_al_fin():
    for valor in ["18:30", "19:00"]:
        data = configuracion_base()
        data["merienda_inicio"] = valor

        es_valido, resultado = validar_configuracion(data)

        assert es_valido is False
        assert resultado["error"] == "El inicio de la merienda debe ser anterior a su fin"
        assert resultado["campos"] == ["merienda_inicio", "merienda_fin"]


def test_comidas_superpuestas():
    data = configuracion_base()
    data["almuerzo_fin"] = "16:30"

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is False
    assert resultado["error"] == "El almuerzo no puede terminar después de que empiece la merienda"
    assert resultado["campos"] == ["almuerzo_fin", "merienda_inicio"]


def test_comida_termina_cuando_empieza_la_siguiente():
    data = configuracion_base()
    data["almuerzo_fin"] = "16:00"

    es_valido, resultado = validar_configuracion(data)

    assert es_valido is True
    assert resultado["almuerzo_fin"] == time(16, 0)


def test_horario_de_corte_invalido():
    for valor in ["25:00", "abc", ""]:
        data = configuracion_base()
        data["horario_corte"] = valor

        es_valido, resultado = validar_configuracion(data)

        assert es_valido is False
        assert resultado["error"] == "El horario de corte debe tener el formato HH:MM"
        assert resultado["campos"] == ["horario_corte"]
