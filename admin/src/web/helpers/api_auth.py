"""Control de acceso y autenticación JWT para los endpoints de la API."""
from functools import wraps
import inspect
import jwt
from flask import request, jsonify, current_app
from src.core.users.models import User


def _obtener_usuario_desde_token():
    """Valida el header Authorization Bearer y retorna (user, error_response)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Token faltante o inválido"}), 401)

    token = auth_header.split(" ", 1)[1].strip()

    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=["HS256"],
            options={"verify_sub": False}
        )
    except jwt.ExpiredSignatureError:
        return None, (jsonify({"error": "Token expirado"}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({"error": "Token inválido"}), 401)

    user_id = payload.get("sub")
    user = User.query.get(user_id)
    if not user or not user.activo:
        return None, (jsonify({"error": "Usuario inactivo o inexistente"}), 401)

    return user, None


def _invocar_con_usuario(f, user, *args, **kwargs):
    """Llama a f pasando current_user=user si la función lo acepta."""
    sig = inspect.signature(f)
    if "current_user" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return f(*args, current_user=user, **kwargs)
    return f(*args, **kwargs)


def token_required(f):
    """Exige un token JWT válido en el header Authorization (Bearer <token>)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user, error = _obtener_usuario_desde_token()
        if error:
            return error

        return _invocar_con_usuario(f, user, *args, **kwargs)

    return decorated_function


def api_permission_required(permission_name):
    """Exige token JWT válido y que el rol del usuario posea el permiso especificado."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user, error = _obtener_usuario_desde_token()
            if error:
                return error

            if not user.role or not any(p.name == permission_name for p in user.role.permissions):
                return jsonify({"error": "No tiene permisos para esta operación."}), 403

            return _invocar_con_usuario(f, user, *args, **kwargs)

        return decorated_function
    return decorator


# Alias de compatibilidad hacia atrás
api_login_required = token_required