"""Manejadores de errores HTTP de la aplicación.

En las rutas de la API (``/api/...``) responden JSON con el formato común
``{"error": "mensaje"}``; en el resto del sitio muestran la página HTML de error.
"""
from flask import jsonify, render_template, request


def _responder_error(codigo, mensaje_api, titulo, descripcion):
    """JSON ``{"error": ...}`` si la ruta es de la API; si no, la página HTML de error."""
    if request.path.startswith("/api/"):
        return jsonify({"error": mensaje_api}), codigo
    return render_template(
        "errors/error.html",
        error_code=codigo,
        error_title=titulo,
        error_description=descripcion
    ), codigo


def forbidden_error(e):
    """Responde el error 403 (acceso denegado)."""
    return _responder_error(
        403,
        "No tiene permisos para esta operación.",
        "Acceso denegado",
        "No tenés los permisos necesarios para realizar esta acción."
    )


def not_found_error(e):
    """Responde el error 404 (recurso inexistente)."""
    return _responder_error(
        404,
        "Recurso no encontrado",
        "Página no encontrada",
        "El recurso que estás buscando no existe o fue movido."
    )


def method_not_allowed_error(e):
    """Responde el error 405 (método HTTP no permitido para la ruta)."""
    return _responder_error(
        405,
        "Método no permitido",
        "Método no permitido",
        "La acción que intentaste no está permitida para esta dirección."
    )


def unauthorized_error(e):
    """Responde el error 401 (no autorizado)."""
    return _responder_error(
        401,
        "No autorizado",
        "No autorizado",
        "No tenés permisos para acceder a esta sección."
    )


def internal_server_error(e):
    """Responde el error 500 sin mostrar el detalle de la excepción.

    Flask ya registra la excepción en el log antes de llamar a este handler.
    """
    return _responder_error(
        500,
        "Error interno del servidor",
        "Error interno del servidor",
        "Ocurrió un problema en el servidor. Intentalo de nuevo más tarde."
    )


def register_error_handlers(app):
    """Registra los manejadores de errores en la aplicación Flask."""
    app.register_error_handler(403, forbidden_error)
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(405, method_not_allowed_error)
    app.register_error_handler(401, unauthorized_error)
    app.register_error_handler(500, internal_server_error)
