"""Validaciones del lado del servidor para la configuración del sistema."""


CAMPOS_PERMITIDOS = {
    "elementos_por_pagina",
    "mantenimiento_activo",
    "mensaje_mantenimiento",
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

    return True, {
        "elementos_por_pagina": elementos_por_pagina,
        "mantenimiento_activo": mantenimiento_activo,
        "mensaje_mantenimiento": mensaje or None,
    }
