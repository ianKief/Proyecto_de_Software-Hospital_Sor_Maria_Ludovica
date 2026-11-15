"""Validaciones del lado del servidor del módulo de Entregas."""
from datetime import date


# --- Cuerpo de POST /api/deliveries ---

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

# --- Query string de GET /api/authorized-meals ---

FILTROS_COMIDAS_AUTORIZADAS = [
    "fecha",
    "dni",
    "nombre",
    "sector_id",
    "tipo_comida_id",
]

# Además de los filtros, el listado acepta el número de página.
PARAMETROS_COMIDAS_AUTORIZADAS = set(FILTROS_COMIDAS_AUTORIZADAS) | {"page"}

# --- Query string de GET /api/deliveries ---

FILTROS_ENTREGAS = [
    "fecha",
    "sector_id",
    "tipo_comida_id",
]

PARAMETROS_ENTREGAS = set(FILTROS_ENTREGAS) | {"page"}

# --- Query string de GET /api/summaries/deliveries ---

# Mismos nombres de parámetros que los otros /api/summaries/* (Julián),
# para que el cliente los use igual. ``estado`` no va: acá solo cuentan
# los pedidos autorizados.
FILTROS_RESUMEN_PERIODO = [
    "fecha_desde",
    "fecha_hasta",
    "sector_id",
    "tipo_comida",
    "tipo_menu",
    "agrupamiento",
]

AGRUPAMIENTOS = ["dia", "semana", "mes", "sector", "comida", "menu"]


# --- Funciones auxiliares ---

def _error(mensaje, campos):
    """Arma el diccionario de error con el formato común de la API."""
    return {
        "error": mensaje,
        "campos": campos,
    }


def _parametros_no_permitidos(args, permitidos):
    """Devuelve el error si en el query string vino algún parámetro fuera de ``permitidos``.

    Si están todos permitidos devuelve ``None``. Los parámetros extra se
    ordenan para que el mensaje salga siempre igual.
    """
    campos_extra = set(args) - set(permitidos)
    if not campos_extra:
        return None
    return _error("Se recibieron parámetros no permitidos", sorted(campos_extra))


def es_id_valido(valor):
    """Indica si ``valor`` sirve como identificador: un entero positivo.

    Se excluye ``bool`` porque en Python ``True`` y ``False`` son ``int``
    (``isinstance(True, int)`` da True), y no queremos aceptarlos como ids.
    """
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def _leer_fecha(texto):
    """Convierte un texto ``AAAA-MM-DD`` en ``date``. Devuelve ``None`` si no es válido."""
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


def _leer_fecha_opcional(args, campo):
    """Lee el parámetro ``campo`` del query string como fecha ``AAAA-MM-DD``.

    Un texto vacío o con solo espacios cuenta como que no vino.
    Devuelve ``(True, fecha)``, con ``fecha`` en ``None`` si no vino,
    o ``(False, error)`` si el formato no es válido.
    """
    texto = args.get(campo, "").strip()
    if not texto:
        return True, None

    fecha = _leer_fecha(texto)
    if fecha is not None:
        return True, fecha

    # El parámetro "fecha" tiene un mensaje propio, que ya usa el cliente.
    if campo == "fecha":
        mensaje = "La fecha debe tener formato AAAA-MM-DD"
    else:
        mensaje = f"{campo} debe tener formato AAAA-MM-DD"
    return False, _error(mensaje, [campo])


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


# --- POST /api/deliveries ---

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
    # Va primero: los otros controles necesitan que sea un diccionario.
    if not isinstance(data, dict):
        return False, _error("El cuerpo debe ser un objeto JSON", [])

    error = _controlar_campos_entrega(data)
    if error:
        return False, error

    error = _controlar_personas(data["personas"])
    if error:
        return False, error

    error = _controlar_ids_entrega(data)
    if error:
        return False, error

    return True, {
        "personas": data["personas"],
        "tipo_comida_id": data["tipo_comida_id"],
        "responsable_id": data["responsable_id"],
    }


def _controlar_campos_entrega(data):
    """Controla que el cuerpo no traiga campos de más ni le falte ninguno.

    Devuelve el error o ``None`` si los campos están bien.
    """
    campos_extra = set(data) - CAMPOS_PERMITIDOS
    if campos_extra:
        return _error("Se recibieron campos no permitidos", sorted(campos_extra))

    faltantes = []
    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in data:
            faltantes.append(campo)

    if faltantes:
        return _error("Faltan campos obligatorios", faltantes)

    return None


def _controlar_personas(personas):
    """Controla que ``personas`` sea una lista no vacía de ids válidos y sin repetir.

    Devuelve el error o ``None`` si la lista está bien.
    """
    if not isinstance(personas, list):
        return _error("personas debe ser una lista", ["personas"])

    if not personas:
        return _error("Debe incluir al menos una persona", ["personas"])

    for persona_id in personas:
        if not es_id_valido(persona_id):
            return _error(
                "Los identificadores de personas deben ser enteros positivos",
                ["personas"],
            )

    if len(personas) != len(set(personas)):
        return _error("No se puede repetir una persona", ["personas"])

    return None


def _controlar_ids_entrega(data):
    """Controla que ``tipo_comida_id`` y ``responsable_id`` sean enteros positivos.

    Devuelve el error o ``None`` si los dos están bien.
    """
    if not es_id_valido(data["tipo_comida_id"]):
        return _error(
            "El tipo de comida debe ser un entero positivo",
            ["tipo_comida_id"],
        )

    if not es_id_valido(data["responsable_id"]):
        return _error(
            "El responsable debe ser un entero positivo",
            ["responsable_id"],
        )

    return None


# --- GET /api/authorized-meals ---

def validar_filtros_comidas_autorizadas(args):
    """Valida el query string de ``GET /api/authorized-meals``.

    ``args`` es ``request.args`` (o cualquier diccionario de textos).
    Los textos vacíos o con solo espacios cuentan como que no vinieron.
    Exige al menos un filtro (``page`` no cuenta) para no traer todo el sistema.

    Devuelve ``(True, filtros)``, con las cinco claves de filtro (las que no
    vinieron en ``None``), o ``(False, {"error": mensaje, "campos": [...]})``.
    """
    error = _parametros_no_permitidos(args, PARAMETROS_COMIDAS_AUTORIZADAS)
    if error:
        return False, error

    textos = {}
    for campo in FILTROS_COMIDAS_AUTORIZADAS:
        texto = args.get(campo, "").strip()
        textos[campo] = texto or None

    if all(texto is None for texto in textos.values()):
        return False, _error(
            "Debe indicar al menos un filtro",
            FILTROS_COMIDAS_AUTORIZADAS,
        )

    filtros = {
        "fecha": None,
        "dni": textos["dni"],
        "nombre": textos["nombre"],
        "sector_id": None,
        "tipo_comida_id": None,
    }

    valida, resultado = _leer_fecha_opcional(args, "fecha")
    if not valida:
        return False, resultado
    filtros["fecha"] = resultado

    for campo in ["sector_id", "tipo_comida_id"]:
        if textos[campo] is not None:
            filtros[campo] = _leer_id(textos[campo])
            if filtros[campo] is None:
                return False, _error(
                    f"{campo} debe ser un entero positivo",
                    [campo],
                )

    return True, filtros


# --- GET /api/authorized-meals/<person_id> ---

def validar_fecha_opcional(args):
    """Valida el query string de ``GET /api/authorized-meals/<person_id>``.

    Solo acepta ``fecha`` (``AAAA-MM-DD``) y es opcional.
    Devuelve ``(True, fecha)``, con ``fecha`` en ``None`` si no vino,
    o ``(False, {"error": mensaje, "campos": [...]})``.
    """
    error = _parametros_no_permitidos(args, {"fecha"})
    if error:
        return False, error

    return _leer_fecha_opcional(args, "fecha")


# --- GET /api/deliveries y GET /api/deliveries/summary ---

def validar_filtros_entregas(args):
    """Valida el query string de ``GET /api/deliveries``.

    ``args`` es ``request.args`` (o cualquier diccionario de textos).
    Los textos vacíos o con solo espacios cuentan como que no vinieron.
    A diferencia de las comidas autorizadas, no exige ningún filtro: si no
    viene ninguno, el endpoint usa los del turno en curso.

    Devuelve ``(True, filtros)``, con las tres claves de filtro (las que no
    vinieron en ``None``), o ``(False, {"error": mensaje, "campos": [...]})``.
    """
    error = _parametros_no_permitidos(args, PARAMETROS_ENTREGAS)
    if error:
        return False, error

    filtros = {
        "fecha": None,
        "sector_id": None,
        "tipo_comida_id": None,
    }

    valida, resultado = _leer_fecha_opcional(args, "fecha")
    if not valida:
        return False, resultado
    filtros["fecha"] = resultado

    for campo in ["sector_id", "tipo_comida_id"]:
        texto = args.get(campo, "").strip()
        if texto:
            filtros[campo] = _leer_id(texto)
            if filtros[campo] is None:
                return False, _error(
                    f"{campo} debe ser un entero positivo",
                    [campo],
                )

    return True, filtros


def validar_filtros_resumen_entregas(args):
    """Valida el query string de ``GET /api/deliveries/summary``.

    Acepta los mismos filtros que el listado de entregas, pero no ``page``,
    porque el resumen no se pagina. Devuelve lo mismo que
    ``validar_filtros_entregas``.
    """
    # Se controla solo "page": los demás parámetros extra los rechaza
    # validar_filtros_entregas, con su propio mensaje.
    if "page" in args:
        return False, _error("Se recibieron parámetros no permitidos", ["page"])

    return validar_filtros_entregas(args)


# --- GET /api/summaries/deliveries ---

def validar_filtros_resumen_periodo(args):
    """Valida el query string de ``GET /api/summaries/deliveries``.

    ``args`` es ``request.args`` (o cualquier diccionario de textos).
    Los textos vacíos o con solo espacios cuentan como que no vinieron.
    Todos los filtros son opcionales. ``tipo_comida`` y ``tipo_menu`` son
    nombres: si existen o no lo controla el núcleo, porque acá no se
    consulta la base.

    Devuelve ``(True, filtros)``, con las seis claves (las que no vinieron
    en ``None``), o ``(False, {"error": mensaje, "campos": [...]})``.
    """
    error = _parametros_no_permitidos(args, FILTROS_RESUMEN_PERIODO)
    if error:
        return False, error

    textos = {}
    for campo in FILTROS_RESUMEN_PERIODO:
        texto = args.get(campo, "").strip()
        textos[campo] = texto or None

    filtros = {
        "fecha_desde": None,
        "fecha_hasta": None,
        "sector_id": None,
        "tipo_comida": textos["tipo_comida"],
        "tipo_menu": textos["tipo_menu"],
        "agrupamiento": textos["agrupamiento"],
    }

    for campo in ["fecha_desde", "fecha_hasta"]:
        valida, resultado = _leer_fecha_opcional(args, campo)
        if not valida:
            return False, resultado
        filtros[campo] = resultado

    if (
        filtros["fecha_desde"] is not None
        and filtros["fecha_hasta"] is not None
        and filtros["fecha_desde"] > filtros["fecha_hasta"]
    ):
        return False, _error(
            "fecha_hasta no puede ser anterior a fecha_desde",
            ["fecha_desde", "fecha_hasta"],
        )

    if textos["sector_id"] is not None:
        filtros["sector_id"] = _leer_id(textos["sector_id"])
        if filtros["sector_id"] is None:
            return False, _error(
                "sector_id debe ser un entero positivo",
                ["sector_id"],
            )

    if (
        filtros["agrupamiento"] is not None
        and filtros["agrupamiento"] not in AGRUPAMIENTOS
    ):
        return False, _error(
            f"agrupamiento debe ser uno de: {', '.join(AGRUPAMIENTOS)}",
            ["agrupamiento"],
        )

    return True, filtros
