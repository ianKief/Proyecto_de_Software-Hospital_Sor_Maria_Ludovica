from flask import render_template

def forbidden_error(e):
    return render_template(
        "errors/error.html",
        error_code=403,
        error_title="Acceso denegado",
        error_description="No tenés los permisos necesarios para realizar esta acción."
    ), 403

def not_found_error(e):
    return render_template(
        "errors/error.html",
        error_code=404,
        error_title="Página no encontrada",
        error_description="El recurso que estás buscando no existe o fue movido."
    ), 404

def unauthorized_error(e):
    return render_template(
        "errors/error.html",
        error_code=401,
        error_title="No autorizado",
        error_description="No tenés permisos para acceder a esta sección."
    ), 401

def internal_server_error(e):
    return render_template(
        "errors/error.html",
        error_code=500,
        error_title="Error interno del servidor",
        error_description="Ocurrió un problema en el servidor. Intentalo de nuevo más tarde."
    ), 500

def register_error_handlers(app):
    """Registra los manejadores de errores en la aplicación Flask."""
    app.register_error_handler(403, forbidden_error)
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(401, unauthorized_error)
    app.register_error_handler(500, internal_server_error)