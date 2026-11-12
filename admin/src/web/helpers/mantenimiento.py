"""Bloqueo del sitio cuando el modo mantenimiento está activo."""
from flask import request, render_template, jsonify

from src.core.configuration import obtener_configuracion
from src.web.helpers.auth import check_permission

# Endpoints de la app web que siempre funcionan, aunque el sitio esté en mantenimiento.
# "auth.login" cubre el GET (formulario) y el POST (procesarlo): es una sola función.
ENDPOINTS_PERMITIDOS = {"static", "auth.login", "auth.logout"}

# Único endpoint de la API que funciona durante el mantenimiento: el portal
# lo consulta para mostrar la pantalla de mantenimiento y para saber si hay
# conexión con el servidor.
ENDPOINTS_API_PERMITIDOS = {"api_configuration.configuration_show"}

PERMISO_MANTENIMIENTO = "config_update"


def verificar_mantenimiento():
    """Corta el pedido con un 503 si el sitio está en mantenimiento.

    Se registra en ``create_app`` con ``app.before_request``, así que Flask
    la llama antes de cada vista. Si devuelve ``None`` el pedido sigue
    normal; si devuelve una respuesta, Flask responde eso y no llama a la vista.

    En ``/api/`` todo responde 503 en JSON con el mensaje, con o sin token
    (también el login), salvo ``GET /api/configuration``.

    En la web siempre pasan el login, el logout, los archivos estáticos y
    quien tenga el permiso ``config_update`` (el Administrador, que es quien
    desactiva el mantenimiento desde Ajustes); el resto ve una página HTML.
    """
    # Cuando agreguemos CORS para el portal, el navegador manda un OPTIONS
    # antes de cada pedido. Si ese OPTIONS recibe 503, el navegador corta la
    # conexión y el portal mostraría "sin conexión" en vez del mantenimiento.
    if request.method == "OPTIONS":
        return None

    # Primero lo exceptuado, para no consultar la base en cada CSS o imagen.
    if request.endpoint in ENDPOINTS_PERMITIDOS:
        return None
    if request.endpoint in ENDPOINTS_API_PERMITIDOS:
        return None

    configuracion = obtener_configuracion()
    if not configuracion.mantenimiento_activo:
        return None

    mensaje = configuracion.mensaje_mantenimiento

    if request.path.startswith("/api/"):
        return jsonify({"error": mensaje}), 503

    if check_permission(PERMISO_MANTENIMIENTO):
        return None
    return render_template("configuration/maintenance.html", mensaje=mensaje), 503
