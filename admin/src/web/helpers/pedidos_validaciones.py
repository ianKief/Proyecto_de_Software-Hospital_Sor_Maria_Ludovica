from datetime import datetime


PERIODICIDADES_VALIDAS = {
    "diaria",
    "semanal",
    "mensual",
}

TIPOS_COMIDA_VALIDOS = {
    "desayuno",
    "almuerzo",
    "merienda",
    "cena",
}


def validar_pedido(data):
    """Valida los datos recibidos para crear un pedido."""

    campos_requeridos = [
        "periodicidad",
        "fecha_desde",
        "fecha_hasta",
        "detalle",
    ]

    faltantes = [
        campo
        for campo in campos_requeridos
        if campo not in data
    ]

    if faltantes:
        return False, {
            "error": "Faltan campos obligatorios",
            "campos": faltantes,
        }

    if data["periodicidad"] not in PERIODICIDADES_VALIDAS:
        return False, {
            "error": "Periodicidad inválida",
            "valores_permitidos": sorted(PERIODICIDADES_VALIDAS),
        }

    try:
        fecha_desde = datetime.strptime(
            data["fecha_desde"],
            "%Y-%m-%d",
        ).date()

        fecha_hasta = datetime.strptime(
            data["fecha_hasta"],
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        return False, {
            "error": "Las fechas deben tener formato YYYY-MM-DD",
        }

    if fecha_hasta < fecha_desde:
        return False, {
            "error": "fecha_hasta no puede ser anterior a fecha_desde",
        }

    detalle = data["detalle"]

    if not isinstance(detalle, dict):
        return False, {
            "error": "detalle debe ser un objeto",
        }

    tipos_desconocidos = set(detalle) - TIPOS_COMIDA_VALIDOS

    if tipos_desconocidos:
        return False, {
            "error": "Se recibieron tipos de comida inválidos",
            "tipos_invalidos": sorted(tipos_desconocidos),
        }

    for tipo_comida in TIPOS_COMIDA_VALIDOS:
        personas = detalle.get(tipo_comida, [])

        if not isinstance(personas, list):
            return False, {
                "error": f"{tipo_comida} debe ser una lista",
            }

        if any(
            not isinstance(persona_id, int) or persona_id <= 0
            for persona_id in personas
        ):
            return False, {
                "error": (
                    f"Los identificadores de personas de {tipo_comida} "
                    "deben ser enteros positivos"
                ),
            }

        if len(personas) != len(set(personas)):
            return False, {
                "error": (
                    f"No se puede repetir una persona en {tipo_comida}"
                ),
            }

    if not any(detalle.get(tipo) for tipo in TIPOS_COMIDA_VALIDOS):
        return False, {
            "error": "Debe existir al menos una persona en alguna comida",
        }

    return True, {
        "periodicidad": data["periodicidad"],
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "detalle": {
            tipo: detalle.get(tipo, [])
            for tipo in TIPOS_COMIDA_VALIDOS
        },
    }