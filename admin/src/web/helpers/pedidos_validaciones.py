from datetime import date, datetime


PERIODICIDADES_VALIDAS = {
    "diaria",
    "semanal",
    "mensual",
}


def validar_pedido(data):
    """Valida los datos recibidos para crear un pedido."""

    campos_requeridos = [
        "periodicidad",
        "fecha_desde",
        "fecha_hasta",
        "personas",
    ]

    faltantes = [
        campo for campo in campos_requeridos
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

    if not isinstance(data["personas"], list) or not data["personas"]:
        return False, {
            "error": "personas debe ser una lista no vacía",
        }

    if not all(isinstance(persona_id, int) for persona_id in data["personas"]):
        return False, {
            "error": "Los identificadores de personas deben ser enteros",
        }

    return True, {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    }