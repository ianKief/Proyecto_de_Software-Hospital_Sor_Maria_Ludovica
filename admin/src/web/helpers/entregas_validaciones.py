"""Validaciones del lado del servidor del módulo de Entregas."""
from datetime import date


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


FILTROS_COMIDAS_AUTORIZADAS = [
    "fecha",
    "dni",
    "nombre",
    "sector_id",
    "tipo_comida_id",
]

# Además de los filtros, el listado acepta el número de página.
PARAMETROS_COMIDAS_AUTORIZADAS = set(FILTROS_COMIDAS_AUTORIZADAS) | {"page"}


def _leer_fecha(texto):
    """Convierte un texto ``AAAA-MM-DD`` en ``date``. Devuelve ``None`` si no es válido."""
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


def _leer_id(texto):
    """Convierte un texto en un entero positivo. Devuelve ``None`` si no es válido.

    Se controla con ``isdecimal()`` antes de ``int()`` porque ``int()`` también
    acepta ``"+5"`` y ``"1_0"`` (que lee como 10). No se usa ``isdigit()``
    porque da True con ``"²"``, que ``int()`` no puede convertir.
    """
    if not texto.isdecimal():
        return None

    valor = int(texto)

    if valor <= 0:
        return None

    return valor


def validar_filtros_comidas_autorizadas(args):
    """Valida el query string de ``GET /api/authorized-meals``.

    ``args`` es ``request.args`` (o cualquier diccionario de textos).
    Los textos vacíos o con solo espacios cuentan como que no vinieron.
    Exige al menos un filtro (``page`` no cuenta) para no traer todo el sistema.

    Devuelve ``(True, filtros)``, con las cinco claves de filtro (las que no
    vinieron en ``None``), o ``(False, {"error": mensaje, "campos": [...]})``.
    """
    campos_extra = set(args) - PARAMETROS_COMIDAS_AUTORIZADAS

    if campos_extra:
        return False, {
            "error": "Se recibieron parámetros no permitidos",
            "campos": sorted(campos_extra),
        }

    textos = {}
    for campo in FILTROS_COMIDAS_AUTORIZADAS:
        texto = args.get(campo, "").strip()
        textos[campo] = texto or None

    if all(texto is None for texto in textos.values()):
        return False, {
            "error": "Debe indicar al menos un filtro",
            "campos": FILTROS_COMIDAS_AUTORIZADAS,
        }

    filtros = {
        "fecha": None,
        "dni": textos["dni"],
        "nombre": textos["nombre"],
        "sector_id": None,
        "tipo_comida_id": None,
    }

    if textos["fecha"] is not None:
        filtros["fecha"] = _leer_fecha(textos["fecha"])
        if filtros["fecha"] is None:
            return False, {
                "error": "La fecha debe tener formato AAAA-MM-DD",
                "campos": ["fecha"],
            }

    for campo in ["sector_id", "tipo_comida_id"]:
        if textos[campo] is not None:
            filtros[campo] = _leer_id(textos[campo])
            if filtros[campo] is None:
                return False, {
                    "error": f"{campo} debe ser un entero positivo",
                    "campos": [campo],
                }

    return True, filtros


FILTROS_ENTREGAS = [
    "fecha",
    "sector_id",
    "tipo_comida_id",
]

PARAMETROS_ENTREGAS = set(FILTROS_ENTREGAS) | {"page"}


def validar_filtros_entregas(args):
    """Valida el query string de ``GET /api/deliveries``.

    ``args`` es ``request.args`` (o cualquier diccionario de textos).
    Los textos vacíos o con solo espacios cuentan como que no vinieron.
    A diferencia de las comidas autorizadas, no exige ningún filtro: si no
    viene ninguno, el endpoint usa los del turno en curso.

    Devuelve ``(True, filtros)``, con las tres claves de filtro (las que no
    vinieron en ``None``), o ``(False, {"error": mensaje, "campos": [...]})``.
    """
    campos_extra = set(args) - PARAMETROS_ENTREGAS

    if campos_extra:
        return False, {
            "error": "Se recibieron parámetros no permitidos",
            "campos": sorted(campos_extra),
        }

    filtros = {
        "fecha": None,
        "sector_id": None,
        "tipo_comida_id": None,
    }

    texto_fecha = args.get("fecha", "").strip()
    if texto_fecha:
        filtros["fecha"] = _leer_fecha(texto_fecha)
        if filtros["fecha"] is None:
            return False, {
                "error": "La fecha debe tener formato AAAA-MM-DD",
                "campos": ["fecha"],
            }

    for campo in ["sector_id", "tipo_comida_id"]:
        texto = args.get(campo, "").strip()
        if texto:
            filtros[campo] = _leer_id(texto)
            if filtros[campo] is None:
                return False, {
                    "error": f"{campo} debe ser un entero positivo",
                    "campos": [campo],
                }

    return True, filtros


def validar_fecha_opcional(args):
    """Valida el query string de ``GET /api/authorized-meals/<person_id>``.

    Solo acepta ``fecha`` (``AAAA-MM-DD``) y es opcional.
    Devuelve ``(True, fecha)``, con ``fecha`` en ``None`` si no vino,
    o ``(False, {"error": mensaje, "campos": [...]})``.
    """
    campos_extra = set(args) - {"fecha"}

    if campos_extra:
        return False, {
            "error": "Se recibieron parámetros no permitidos",
            "campos": sorted(campos_extra),
        }

    texto = args.get("fecha", "").strip()

    if not texto:
        return True, None

    fecha = _leer_fecha(texto)

    if fecha is None:
        return False, {
            "error": "La fecha debe tener formato AAAA-MM-DD",
            "campos": ["fecha"],
        }

    return True, fecha
