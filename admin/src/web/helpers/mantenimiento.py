"""Bloqueo del sitio cuando el modo mantenimiento está activo."""
from flask import request, render_template, jsonify

from src.core.configuration import obtener_configuracion
from src.web.helpers.auth import check_permission, is_authenticated

# Endpoints que siempre funcionan, aunque el sitio esté en mantenimiento.
# "auth.login" cubre el GET (formulario) y el POST (procesarlo): es una sola función.
ENDPOINTS_PERMITIDOS = {"static", "auth.login", "auth.logout"}


def verificar_mantenimiento():
    """Corta el pedido con un 503 si el sitio está en mantenimiento.

    Se registra en ``create_app`` con ``app.before_request``, así que Flask
    la llama antes de cada vista. Si devuelve ``None`` el pedido sigue
    normal; si devuelve una respuesta, Flask responde eso y no llama a la vista.

    Siempre pasan el login, el logout, los archivos estáticos y quien tenga
    el permiso ``config_update`` (el Administrador, que es quien puede
    desactivar el mantenimiento). En ``/api/`` responde JSON; en el resto,
    una página HTML con el mensaje.

    En ``/api/`` también pasa el pedido sin sesión: la spec pide que el 401
    vaya antes que cualquier otra regla, y ese 401 lo da el decorador de la
    vista (``api_login_required``).
    """
    # Primero lo exceptuado, para no consultar la base en cada CSS o imagen.
    if request.endpoint in ENDPOINTS_PERMITIDOS:
        return None

    # Sin sesión en la API: que siga, así la vista responde 401 y no 503.
    if request.path.startswith("/api/") and not is_authenticated():
        return None

    configuracion = obtener_configuracion()
    if not configuracion.mantenimiento_activo:
        return None

    if check_permission("config_update"):
        return None

    mensaje = configuracion.mensaje_mantenimiento
    if request.path.startswith("/api/"):
        return jsonify({"error": mensaje}), 503
    return render_template("configuration/maintenance.html", mensaje=mensaje), 503
