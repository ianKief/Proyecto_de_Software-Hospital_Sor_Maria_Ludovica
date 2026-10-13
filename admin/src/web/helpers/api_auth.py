"""Control de acceso para los endpoints de la API."""
from functools import wraps

from flask import jsonify

from src.web.helpers.auth import (
    check_permission,
    is_authenticated,
)


def api_login_required(f):
    """Exige una sesión iniciada y responde en JSON."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return jsonify({
                "error": "Debe iniciar sesión."
            }), 401

        return f(*args, **kwargs)

    return decorated_function


def api_permission_required(permission_name):
    """Exige sesión iniciada y un permiso específico."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                return jsonify({
                    "error": "Debe iniciar sesión."
                }), 401

            if not check_permission(permission_name):
                return jsonify({
                    "error": "No tiene permisos para esta operación."
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator