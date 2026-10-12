"""Validaciones del lado del servidor para registrar una entrega."""


CAMPOS_PERMITIDOS = {
    "personas",
    "tipo_comida_id",
    "responsable_id",
}

# Lista (y no set) para que los faltantes salgan siempre en el mismo orden.
CAMPOS_OBLIGATORIOS = [
    "personas",
    "tipo_comida_id",
    "responsable_id",
]


def es_id_valido(valor):
    """Indica si ``valor`` sirve como identificador: un entero positivo.

    Se excluye ``bool`` porque en Python ``True`` y ``False`` son ``int``
    (``isinstance(True, int)`` da True), y no queremos aceptarlos como ids.
    """
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def validar_entrega(data):
    """Valida el JSON recibido en ``POST /api/deliveries``.

    Solo revisa el formato: no consulta la base. Que las personas,
    el responsable y el tipo de comida existan, y que haya autorización
    vigente, se controla al registrar la entrega.

    No convierte textos a número: en JSON los ids llegan como números,
    así que ``"3"`` se rechaza.

    Devuelve ``(True, datos_limpios)`` si todo es válido, o
    ``(False, {"error": mensaje, "campos": [...]})`` con el primer error encontrado.
    """

    if not isinstance(data, dict):
        return False, {
            "error": "El cuerpo debe ser un objeto JSON",
            "campos": [],
        }

    campos_extra = set(data) - CAMPOS_PERMITIDOS

    if campos_extra:
        return False, {
            "error": "Se recibieron campos no permitidos",
            "campos": sorted(campos_extra),
        }

    faltantes = [campo for campo in CAMPOS_OBLIGATORIOS if campo not in data]

    if faltantes:
        return False, {
            "error": "Faltan campos obligatorios",
            "campos": faltantes,
        }

    personas = data["personas"]

    if not isinstance(personas, list):
        return False, {
            "error": "personas debe ser una lista",
            "campos": ["personas"],
        }

    if not personas:
        return False, {
            "error": "Debe incluir al menos una persona",
            "campos": ["personas"],
        }

    if not all(es_id_valido(persona_id) for persona_id in personas):
        return False, {
            "error": "Los identificadores de personas deben ser enteros positivos",
            "campos": ["personas"],
        }

    if len(personas) != len(set(personas)):
        return False, {
            "error": "No se puede repetir una persona",
            "campos": ["personas"],
        }

    if not es_id_valido(data["tipo_comida_id"]):
        return False, {
            "error": "El tipo de comida debe ser un entero positivo",
            "campos": ["tipo_comida_id"],
        }

    if not es_id_valido(data["responsable_id"]):
        return False, {
            "error": "El responsable debe ser un entero positivo",
            "campos": ["responsable_id"],
        }

    return True, {
        "personas": personas,
        "tipo_comida_id": data["tipo_comida_id"],
        "responsable_id": data["responsable_id"],
    }
