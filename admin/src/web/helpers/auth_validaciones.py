"""Validaciones de datos de entrada y reglas de acceso para la autenticación en la API."""
import re
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

# Roles que operan en la aplicación pública (portal).
# El rol Administrador utiliza exclusivamente la aplicación privada de administración.
ROLES_OPERATIVOS_PORTAL = {
    "Jefe de Servicio",
    "Servicio de Alimentación",
    "Sector Comedor",
}

EMISORES_GOOGLE_VALIDOS = {
    "accounts.google.com",
    "https://accounts.google.com",
}

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PATRON_NOMBRE_APELLIDO = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s'-]{2,100}$")
PATRON_DNI = re.compile(r"^\d{7,8}$")


def es_rol_operativo_portal(user):
    """Indica si el usuario tiene asignado uno de los roles operativos del portal."""
    return bool(user and user.role and user.role.name in ROLES_OPERATIVOS_PORTAL)


def validar_datos_login_api(data):
    """Valida el cuerpo JSON recibido en POST /api/auth/login.

    Retorna ``(datos_limpios, mensaje_error)``. Si hay error, ``datos_limpios`` es ``None``.
    """
    if data is None or not isinstance(data, dict):
        return None, "Formato JSON inválido o faltante."

    email = data.get("email")
    password = data.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        return None, "Debe proporcionar email y contraseña válidos."

    email = email.strip()
    if not email or not password:
        return None, "Debe proporcionar email y contraseña."

    if not PATRON_EMAIL.match(email):
        return None, "El formato del correo electrónico no es válido."

    return {"email": email, "password": password}, None


def validar_datos_google_login_api(data):
    """Extrae y valida la presencia del ID token de Google en POST /api/auth/google.

    Acepta el campo ``id_token`` (o ``credential``, como lo entrega Google Identity Services).
    Retorna ``(token_str, mensaje_error)``.
    """
    if data is None or not isinstance(data, dict):
        return None, "Formato JSON inválido o faltante."

    raw_token = data.get("id_token") or data.get("credential")
    if not isinstance(raw_token, str) or not raw_token.strip():
        return None, "Debe proporcionar el token de identidad de Google (id_token)."

    return raw_token.strip(), None


def verificar_id_token_google(token_str, client_id):
    """Verifica criptográficamente el ID token de Google (firma, emisor, audiencia y vencimiento).

    Retorna ``(email_verificado, mensaje_error)``.
    """
    if not client_id or not str(client_id).strip():
        return None, "El inicio de sesión con Google no tiene un Client ID configurado."

    try:
        idinfo = google_id_token.verify_oauth2_token(
            token_str,
            google_requests.Request(),
            audience=client_id.strip(),
        )
    except Exception:
        return None, "El token de identidad de Google es inválido o ha expirado."

    if idinfo.get("iss") not in EMISORES_GOOGLE_VALIDOS:
        return None, "El emisor del token de identidad no es válido."

    if idinfo.get("aud") != client_id.strip():
        return None, "La audiencia del token no coincide con la aplicación."

    email = idinfo.get("email")
    email_verificado = idinfo.get("email_verified")
    if not email or not isinstance(email, str) or not email_verificado:
        return None, "La cuenta de Google no posee un correo electrónico verificado."

    return email.strip(), None


def validar_acceso_usuario_portal(user):
    """Verifica que el usuario esté activo y tenga un rol habilitado para usar el portal.

    Retorna ``(mensaje_error, status_code)`` si el acceso debe rechazarse,
    o ``(None, None)`` si el usuario puede ingresar.
    """
    if not user.activo:
        return "La cuenta se encuentra bloqueada o inactiva. Contacte al Administrador.", 403

    if user.role and user.role.name == "Administrador":
        return "Los usuarios con rol Administrador deben ingresar desde el panel de administración.", 403

    if not es_rol_operativo_portal(user):
        return "Su rol no se encuentra habilitado para acceder al portal.", 403

    return None, None


def validar_datos_perfil_api(data):
    """Valida los campos enviados en PUT /api/auth/me para actualizar el propio perfil.

    Retorna ``(datos_limpios, errores_campos, mensaje_error)``.
    Si los datos son válidos, ``errores_campos`` y ``mensaje_error`` son ``None``.
    """
    if data is None or not isinstance(data, dict):
        return None, {}, "Formato JSON inválido o faltante."

    errores = {}

    nombre = (data.get("nombre") or "").strip() if isinstance(data.get("nombre"), str) else ""
    apellido = (data.get("apellido") or "").strip() if isinstance(data.get("apellido"), str) else ""
    email = (data.get("email") or "").strip() if isinstance(data.get("email"), str) else ""
    dni = str(data.get("dni") or "").strip() if isinstance(data.get("dni"), (str, int)) else ""

    password_raw = data.get("password")
    password_confirm_raw = data.get("password_confirm")
    password = password_raw if isinstance(password_raw, str) else ""
    password_confirm = password_confirm_raw if isinstance(password_confirm_raw, str) else ""

    if not nombre:
        errores["nombre"] = "El nombre es obligatorio."
    elif not PATRON_NOMBRE_APELLIDO.match(nombre):
        errores["nombre"] = "El nombre solo puede contener letras y debe tener entre 2 y 100 caracteres."

    if not apellido:
        errores["apellido"] = "El apellido es obligatorio."
    elif not PATRON_NOMBRE_APELLIDO.match(apellido):
        errores["apellido"] = "El apellido solo puede contener letras y debe tener entre 2 y 100 caracteres."

    if not email:
        errores["email"] = "El correo electrónico es obligatorio."
    elif not PATRON_EMAIL.match(email) or len(email) > 120:
        errores["email"] = "El formato del correo electrónico no es válido."

    if not dni:
        errores["dni"] = "El DNI es obligatorio."
    elif not PATRON_DNI.match(dni):
        errores["dni"] = "El DNI debe contener únicamente números (entre 7 y 8 dígitos)."

    # La contraseña es opcional al editar el perfil; solo se valida si el usuario escribió algo
    if password or password_confirm:
        if len(password.strip()) < 6:
            errores["password"] = "La nueva contraseña debe tener al menos 6 caracteres."
        elif password_confirm_raw is not None and password != password_confirm:
            errores["password_confirm"] = "Las contraseñas ingresadas no coinciden."

    if errores:
        primer_error = next(iter(errores.values()))
        return None, errores, primer_error

    return {
        "nombre": nombre,
        "apellido": apellido,
        "email": email,
        "dni": dni,
        "password": password if password.strip() else None,
    }, None, None
