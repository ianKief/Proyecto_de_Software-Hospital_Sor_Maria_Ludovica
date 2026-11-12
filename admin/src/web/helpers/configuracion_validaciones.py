"""Validaciones del lado del servidor para la configuración del sistema."""
from datetime import datetime


# Las comidas en el orden en que ocurren en el día: se usa para controlar
# que una comida no se superponga con la siguiente.
COMIDAS_EN_ORDEN = ["desayuno", "almuerzo", "merienda", "cena"]

# Con el artículo, para armar mensajes con el género correcto.
COMIDAS_CON_ARTICULO = {
    "desayuno": "el desayuno",
    "almuerzo": "el almuerzo",
    "merienda": "la merienda",
    "cena": "la cena",
}

CAMPOS_HORARIOS = [
    "desayuno_inicio",
    "desayuno_fin",
    "almuerzo_inicio",
    "almuerzo_fin",
    "merienda_inicio",
    "merienda_fin",
    "cena_inicio",
    "cena_fin",
    "horario_corte",
]

# Nombre legible de cada horario, para los mensajes de error.
NOMBRES_HORARIOS = {
    "desayuno_inicio": "inicio del desayuno",
    "desayuno_fin": "fin del desayuno",
    "almuerzo_inicio": "inicio del almuerzo",
    "almuerzo_fin": "fin del almuerzo",
    "merienda_inicio": "inicio de la merienda",
    "merienda_fin": "fin de la merienda",
    "cena_inicio": "inicio de la cena",
    "cena_fin": "fin de la cena",
    "horario_corte": "horario de corte",
}

FORMATO_HORA = "%H:%M"

CAMPOS_PERMITIDOS = {
    "elementos_por_pagina",
    "mantenimiento_activo",
    "mensaje_mantenimiento",
    *CAMPOS_HORARIOS,
}

# Campos que agrega el propio formulario HTML: se ignoran, no son datos de la configuración.
CAMPOS_DEL_FORMULARIO = {
    "csrf_token",
    "submit",
}

ELEMENTOS_MINIMO = 1
ELEMENTOS_MAXIMO = 25
LARGO_MAXIMO_MENSAJE = 255


def validar_configuracion(data):
    """Valida los datos recibidos para actualizar la configuración.

    Recibe un diccionario (por ejemplo, ``request.form.to_dict()``).
    Ignora ``csrf_token`` y ``submit``, y rechaza cualquier otro campo
    que no sea de la configuración. Si falta ``mantenimiento_activo``
    se toma como False, porque un checkbox destildado no se envía.
    Al final valida los horarios con ``validar_horarios`` y los agrega
    a los datos limpios como ``datetime.time``.

    Devuelve ``(True, datos_limpios)`` si todo es válido, o
    ``(False, {"error": mensaje, "campos": [...]})`` con el primer error encontrado.
    """

    campos_extra = set(data) - CAMPOS_PERMITIDOS - CAMPOS_DEL_FORMULARIO

    if campos_extra:
        return False, {
            "error": "Se recibieron campos no permitidos",
            "campos": sorted(campos_extra),
        }

    if "elementos_por_pagina" not in data:
        return False, {
            "error": "Faltan campos obligatorios",
            "campos": ["elementos_por_pagina"],
        }

    try:
        elementos_por_pagina = int(str(data["elementos_por_pagina"]).strip())
    except ValueError:
        return False, {
            "error": "Los elementos por página deben ser un número entero",
            "campos": ["elementos_por_pagina"],
        }

    if not ELEMENTOS_MINIMO <= elementos_por_pagina <= ELEMENTOS_MAXIMO:
        return False, {
            "error": (
                f"Los elementos por página deben estar entre "
                f"{ELEMENTOS_MINIMO} y {ELEMENTOS_MAXIMO}"
            ),
            "campos": ["elementos_por_pagina"],
        }

    valor_mantenimiento = data.get("mantenimiento_activo", False)

    # Se usa "is" y no "in (True, 'on')" porque en Python 1 == True.
    if valor_mantenimiento is True or valor_mantenimiento == "on":
        mantenimiento_activo = True
    elif valor_mantenimiento is False:
        mantenimiento_activo = False
    else:
        return False, {
            "error": "El valor de mantenimiento activo es inválido",
            "campos": ["mantenimiento_activo"],
        }

    mensaje = data.get("mensaje_mantenimiento", "")

    if not isinstance(mensaje, str):
        return False, {
            "error": "El mensaje de mantenimiento debe ser un texto",
            "campos": ["mensaje_mantenimiento"],
        }

    mensaje = mensaje.strip()

    if len(mensaje) > LARGO_MAXIMO_MENSAJE:
        return False, {
            "error": (
                f"El mensaje de mantenimiento no puede superar los "
                f"{LARGO_MAXIMO_MENSAJE} caracteres"
            ),
            "campos": ["mensaje_mantenimiento"],
        }

    if mantenimiento_activo and not mensaje:
        return False, {
            "error": "El mensaje es obligatorio si el mantenimiento está activo",
            "campos": ["mensaje_mantenimiento"],
        }

    horarios_validos, resultado_horarios = validar_horarios(data)

    if not horarios_validos:
        return False, resultado_horarios

    datos_limpios = {
        "elementos_por_pagina": elementos_por_pagina,
        "mantenimiento_activo": mantenimiento_activo,
        "mensaje_mantenimiento": mensaje or None,
    }
    datos_limpios.update(resultado_horarios)
    return True, datos_limpios


def convertir_hora(valor):
    """Convierte un texto "HH:MM" en un ``datetime.time``.

    Devuelve None si el valor no es un texto o no tiene ese formato
    (por ejemplo "25:00", "abc" o "").
    """
    if not isinstance(valor, str):
        return None

    try:
        return datetime.strptime(valor.strip(), FORMATO_HORA).time()
    except ValueError:
        return None


def validar_horarios(data):
    """Valida los horarios de las comidas y el horario de corte.

    Los 9 campos son obligatorios y tienen formato HH:MM. Cada comida
    tiene que empezar antes de terminar, y no puede terminar después de
    que empiece la siguiente (puede terminar justo cuando empieza).
    El horario de corte solo se controla que tenga formato válido,
    porque es una hora del día anterior y no se compara con las comidas.

    Devuelve ``(True, horas)`` con un ``datetime.time`` por campo, o
    ``(False, {"error": mensaje, "campos": [...]})`` con el primer error.
    """
    faltantes = []
    for campo in CAMPOS_HORARIOS:
        if campo not in data:
            faltantes.append(campo)

    if faltantes:
        return False, {"error": "Faltan campos obligatorios", "campos": faltantes}

    horas = {}
    for campo in CAMPOS_HORARIOS:
        hora = convertir_hora(data[campo])
        if hora is None:
            return False, {
                "error": f"El {NOMBRES_HORARIOS[campo]} debe tener el formato HH:MM",
                "campos": [campo],
            }
        horas[campo] = hora

    error = _verificar_inicio_antes_de_fin(horas)
    if error:
        return False, error

    error = _verificar_sin_superposicion(horas)
    if error:
        return False, error

    return True, horas


def _verificar_inicio_antes_de_fin(horas):
    """Devuelve el error de la primera comida que no empieza antes de terminar, o None."""
    for comida in COMIDAS_EN_ORDEN:
        inicio = f"{comida}_inicio"
        fin = f"{comida}_fin"
        if horas[inicio] >= horas[fin]:
            return {
                "error": f"El {NOMBRES_HORARIOS[inicio]} debe ser anterior a su fin",
                "campos": [inicio, fin],
            }
    return None


def _verificar_sin_superposicion(horas):
    """Devuelve el error de la primera comida que se superpone con la siguiente, o None.

    Que una comida termine a la misma hora en que empieza la siguiente es válido.
    """
    for posicion in range(len(COMIDAS_EN_ORDEN) - 1):
        anterior = COMIDAS_EN_ORDEN[posicion]
        siguiente = COMIDAS_EN_ORDEN[posicion + 1]
        fin_anterior = f"{anterior}_fin"
        inicio_siguiente = f"{siguiente}_inicio"
        if horas[fin_anterior] > horas[inicio_siguiente]:
            return {
                "error": (
                    f"{COMIDAS_CON_ARTICULO[anterior].capitalize()} no puede terminar "
                    f"después de que empiece {COMIDAS_CON_ARTICULO[siguiente]}"
                ),
                "campos": [fin_anterior, inicio_siguiente],
            }
    return None
