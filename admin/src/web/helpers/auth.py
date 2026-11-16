"""Helpers de sesión, autenticación y control de permisos para la aplicación privada."""
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash, abort
from src.core.db import db
from src.core.users.models import User

# Tiempo máximo que puede permanecer abierta una sesión sin actividad antes de expirar
TIMEOUT_INACTIVIDAD = timedelta(minutes=30)


def is_authenticated():
    """Indica si existe una sesión de usuario activa en el navegador actual.

    Revisa si la clave ``user`` está presente dentro de la sesión de Flask.
    """
    return session.get("user") is not None


def get_current_user():
    """Devuelve el usuario logueado, o None si no hay sesión.

    Se registra como función global en Jinja para que las plantillas (como el layout)
    puedan consultar los datos del usuario autenticado en cualquier vista.
    """
    if not is_authenticated():
        return None
    return db.session.get(User, session.get("user_id"))


def es_administrador(user=None):
    """Comprueba si el usuario indicado (o el de la sesión actual) es un Administrador activo.

    Se utiliza para asegurar que la aplicación privada y sus funcionalidades de perfil
    sean exclusivas para el rol Administrador.
    """
    if user is None:
        user = get_current_user()
    return bool(user and user.activo and user.role and user.role.name == "Administrador")


def verificar_timeout_sesion():
    """Cierra la sesión automáticamente si el usuario estuvo inactivo más de 30 minutos.

    Se ejecuta antes de cada petición (`before_request`). Compara la hora actual con
    la última actividad guardada en `session["last_activity"]`. Si superó el tiempo
    límite, borra la sesión y redirige al login; de lo contrario, renueva la marca de tiempo.
    """
    if not is_authenticated():
        return

    ultima_actividad = session.get("last_activity")
    ahora = datetime.now(timezone.utc)

    if ultima_actividad:
        ultima = datetime.fromisoformat(ultima_actividad)
        if ahora - ultima > TIMEOUT_INACTIVIDAD:
            session.clear()
            flash("Tu sesión expiró por inactividad. Por favor, volvé a iniciar sesión.", "error")
            return redirect(url_for("auth.login"))

    session["last_activity"] = ahora.isoformat()


def login_required(f):
    """Decorador para vistas que requieren que el usuario haya iniciado sesión.

    Si no hay sesión activa, muestra un mensaje de error y redirige al formulario de login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash("Debe iniciar sesión para acceder a esta página.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorador que restringe una vista exclusivamente a usuarios con rol Administrador.

    Si el usuario no inició sesión lo envía al login, y si tiene otro rol responde con 403.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash("Debe iniciar sesión para acceder a esta página.", "error")
            return redirect(url_for("auth.login"))
        if not es_administrador():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def check_permission(permission_name):
    """Verifica si el usuario en sesión está activo y su rol incluye el permiso pedido.

    Recibe el nombre interno del permiso (por ejemplo ``"user_index"``) y devuelve
    ``True`` si lo posee o ``False`` en caso contrario.
    """
    if not is_authenticated():
        return False

    user = db.session.get(User, session.get("user_id"))
    if not user or not user.activo or not user.role:
        return False

    for p in user.role.permissions:
        if p.name == permission_name:
            return True

    return False


def permission_required(permission_name):
    """Decorador para proteger vistas según un permiso puntual del rol del usuario.

    Si no hay sesión redirige al login; si el usuario está logueado pero su rol no
    tiene el permiso ``permission_name``, corta la ejecución con un error 403.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                flash("Debe iniciar sesión para acceder a esta página.", "error")
                return redirect(url_for("auth.login"))
            if not check_permission(permission_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
