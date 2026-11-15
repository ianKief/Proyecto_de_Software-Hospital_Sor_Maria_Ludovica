"""Validaciones del lado del servidor del módulo de Entregas."""
import re
from datetime import date


# --- Cuerpo de POST /api/deliveries ---

CAMPOS_PERMITIDOS = {
    "personas",
    "tipo_comida_id",
    "responsable_id",
    "responsable_dni",
    "responsable_nombre",
}

# Lista (y no set) para que los faltantes salgan siempre en el mismo orden.
# El responsable no es obligatorio: con una sola persona, es ella (Etapa 2).
CAMPOS_OBLIGATORIOS = [
    "personas",
    "tipo_comida_id",
]

# Mismo formato de DNI que usa Personal (src/core/personnel/validators.py):
# de 7 a 9 dígitos, sin puntos ni espacios.
PATRON_DNI = re.compile(r"\d{7,9}")

# Mismo largo que la columna responsable_nombre (y que Personal.nombre).
LARGO_MAXIMO_NOMBRE = 255

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
    Los datos limpios traen siempre ``responsable_id``, ``responsable_dni`` y
    ``responsable_nombre`` (los que no corresponden, en ``None``).
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

    error = _controlar_tipo_comida(data["tipo_comida_id"])
    if error:
        return False, error

    error = _controlar_responsable(data)
    if error:
        return False, error

    datos_limpios = {
        "personas": data["personas"],
        "tipo_comida_id": data["tipo_comida_id"],
    }
    datos_limpios.update(_datos_del_responsable(data))
    return True, datos_limpios


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


def _controlar_tipo_comida(tipo_comida_id):
    """Controla que ``tipo_comida_id`` sea un entero positivo.

    Devuelve el error o ``None`` si está bien.
    """
    if not es_id_valido(tipo_comida_id):
        return _error(
            "El tipo de comida debe ser un entero positivo",
            ["tipo_comida_id"],
        )
    return None


def _vino(data, campo):
    """Indica si el cliente mandó ``campo`` con algún valor.

    Un campo en ``null`` cuenta como que no vino: así el formulario puede
    mandar los tres campos del responsable y dejar en ``null`` los que no usa.
    """
    return data.get(campo) is not None


def _controlar_responsable(data):
    """Controla quién retira la entrega.

    Puede ser una de las personas de la entrega (``responsable_id``) o un
    tercero (``responsable_dni`` y ``responsable_nombre``), pero no las dos
    cosas. Si no viene ninguno, solo se acepta cuando la entrega es de una
    sola persona (ella es el responsable). Devuelve el error o ``None``.
    """
    viene_id = _vino(data, "responsable_id")
    viene_tercero = (
        _vino(data, "responsable_dni") or _vino(data, "responsable_nombre")
    )

    if viene_id and viene_tercero:
        return _error(
            "Indique responsable_id o el DNI y nombre de un tercero, no ambos",
            ["responsable_id", "responsable_dni", "responsable_nombre"],
        )

    if viene_id:
        return _controlar_responsable_incluido(data)

    if viene_tercero:
        return _controlar_tercero(data)

    if len(data["personas"]) > 1:
        return _error(
            "El responsable es obligatorio cuando el retiro incluye más de una persona",
            ["responsable_id"],
        )

    return None


def _controlar_responsable_incluido(data):
    """Controla que ``responsable_id`` sea un id válido y una de las personas de la entrega.

    Si retira alguien que no está en la entrega (aunque esté en Personal),
    se registra como tercero con DNI y nombre.
    Devuelve el error o ``None``.
    """
    responsable_id = data["responsable_id"]

    if not es_id_valido(responsable_id):
        return _error(
            "El responsable debe ser un entero positivo",
            ["responsable_id"],
        )

    if responsable_id not in data["personas"]:
        return _error(
            "El responsable debe ser una de las personas de la entrega; "
            "si retira otra persona, envíe responsable_dni y responsable_nombre",
            ["responsable_id"],
        )

    return None


def _controlar_tercero(data):
    """Controla el DNI y el nombre del tercero que retira.

    Hacen falta los dos. El DNI va como texto, con el mismo formato que
    Personal. Devuelve el error o ``None``.
    """
    faltantes = []
    for campo in ["responsable_dni", "responsable_nombre"]:
        if not _vino(data, campo):
            faltantes.append(campo)

    if faltantes:
        return _error("Para un tercero se necesitan el DNI y el nombre", faltantes)

    dni = data["responsable_dni"]
    if not isinstance(dni, str) or not PATRON_DNI.fullmatch(dni.strip()):
        return _error(
            "El DNI del responsable debe tener entre 7 y 9 números, sin puntos ni espacios",
            ["responsable_dni"],
        )

    nombre = data["responsable_nombre"]
    if not isinstance(nombre, str) or not nombre.strip():
        return _error(
            "El nombre del responsable no puede estar vacío",
            ["responsable_nombre"],
        )

    if len(nombre.strip()) > LARGO_MAXIMO_NOMBRE:
        return _error(
            f"El nombre del responsable no puede superar los {LARGO_MAXIMO_NOMBRE} caracteres",
            ["responsable_nombre"],
        )

    return None


def _datos_del_responsable(data):
    """Arma las tres claves del responsable para los datos limpios.

    Se llama después de ``_controlar_responsable``, así que los datos ya
    son válidos. Las claves que no corresponden quedan en ``None``.
    """
    if _vino(data, "responsable_dni"):
        return {
            "responsable_id": None,
            "responsable_dni": data["responsable_dni"].strip(),
            "responsable_nombre": data["responsable_nombre"].strip(),
        }

    responsable_id = data.get("responsable_id")
    if responsable_id is None:
        # Con una sola persona y sin responsable, retira ella misma.
        responsable_id = data["personas"][0]

    return {
        "responsable_id": responsable_id,
        "responsable_dni": None,
        "responsable_nombre": None,
    }


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
