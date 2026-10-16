"""Bloqueo del sitio cuando el modo mantenimiento está activo."""
from flask import request, render_template, jsonify

from src.core.configuration import obtener_configuracion
from src.web.helpers.auth import check_permission
# Reusa la lectura del token de api_auth para no duplicar la validación
from src.web.helpers.api_auth import _obtener_usuario_desde_token

# Endpoints que siempre funcionan, aunque el sitio esté en mantenimiento.
# "auth.login" cubre el GET (formulario) y el POST (procesarlo): es una sola función.
ENDPOINTS_PERMITIDOS = {"static", "auth.login", "auth.logout"}

PERMISO_MANTENIMIENTO = "config_update"


def _usuario_tiene_permiso(usuario, nombre_permiso):
    """Indica si el rol de ``usuario`` tiene el permiso ``nombre_permiso``."""
    if not usuario.role:
        return False
    return any(p.name == nombre_permiso for p in usuario.role.permissions)


def verificar_mantenimiento():
    """Corta el pedido con un 503 si el sitio está en mantenimiento.

    Se registra en ``create_app`` con ``app.before_request``, así que Flask
    la llama antes de cada vista. Si devuelve ``None`` el pedido sigue
    normal; si devuelve una respuesta, Flask responde eso y no llama a la vista.

    Siempre pasan el login, el logout, los archivos estáticos y quien tenga
    el permiso ``config_update`` (el Administrador, que es quien puede
    desactivar el mantenimiento). En la web el usuario sale de la sesión y
    se muestra una página HTML; en ``/api/`` sale del token JWT y se
    responde JSON.

    En ``/api/`` también pasa el pedido sin un token válido: la spec pide
    que el 401 vaya antes que cualquier otra regla, y ese 401 lo da el
    decorador de la vista (``api_login_required`` o ``api_permission_required``).
    """
    # Primero lo exceptuado, para no consultar la base en cada CSS o imagen.
    if request.endpoint in ENDPOINTS_PERMITIDOS:
        return None

    configuracion = obtener_configuracion()
    if not configuracion.mantenimiento_activo:
        return None

    mensaje = configuracion.mensaje_mantenimiento

    if request.path.startswith("/api/"):
        # El error se ignora: token ausente, inválido, expirado o usuario
        # inactivo siguen de largo para que la vista responda 401 y no 503.
        usuario, _error = _obtener_usuario_desde_token()
        if usuario is None:
            return None
        if _usuario_tiene_permiso(usuario, PERMISO_MANTENIMIENTO):
            return None
        return jsonify({"error": mensaje}), 503

    if check_permission(PERMISO_MANTENIMIENTO):
        return None
    return render_template("configuration/maintenance.html", mensaje=mensaje), 503
