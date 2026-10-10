"""Control de acceso para los endpoints de la API (respuestas en JSON)."""
from functools import wraps

from flask import jsonify

from src.web.helpers.auth import is_authenticated


def api_login_required(f):
    """Deja pasar solo a usuarios con sesión; si no hay sesión, responde 401 en JSON.

    Es la versión para la API de ``login_required``: en vez de redirigir al
    login (HTML), devuelve ``{"error": ...}`` con código 401.
    Por ahora usa la sesión de Flask. Cuando exista la autenticación por
    token (issue #12), se cambia solo este decorador y los endpoints no cambian.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Debe iniciar sesión."}), 401
        return f(*args, **kwargs)
    return decorated_function
