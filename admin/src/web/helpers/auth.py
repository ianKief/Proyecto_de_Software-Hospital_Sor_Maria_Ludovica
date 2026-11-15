from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import session, redirect, url_for, flash, abort
from src.core.db import db
from src.core.users.models import User

TIMEOUT_INACTIVIDAD = timedelta(minutes=30)


def is_authenticated():
    return session.get("user") is not None


def get_current_user():
    """Devuelve el usuario logueado, o None si no hay sesión.

    Se registra como global de Jinja para que el layout pueda mostrar
    el nombre y apellido del usuario.
    """
    if not is_authenticated():
        return None
    return db.session.get(User, session.get("user_id"))


def es_administrador(user=None):
    """Verifica si el usuario recibido (o el usuario en sesión) está activo y tiene rol Administrador."""
    if user is None:
        user = get_current_user()
    return bool(user and user.activo and user.role and user.role.name == "Administrador")


def verificar_timeout_sesion():
    """Cierra la sesión automáticamente si el usuario estuvo inactivo más de 30 minutos.
    
    Debe registrarse como before_request en la app de Flask.
    En cada request compara la hora actual con la última actividad registrada en la sesión.
    Si el tiempo transcurrido supera el límite, limpia la sesión y redirige al login.
    Si la sesión sigue vigente, actualiza el timestamp de última actividad.
    """
    # Solo actúa si hay una sesión abierta
    if not is_authenticated():
        return

    ultima_actividad = session.get("last_activity")
    ahora = datetime.now(timezone.utc)

    if ultima_actividad:
        # Reconstituir el datetime desde ISO string
        ultima = datetime.fromisoformat(ultima_actividad)
        if ahora - ultima > TIMEOUT_INACTIVIDAD:
            session.clear()
            flash("Tu sesión expiró por inactividad. Por favor, volvé a iniciar sesión.", "error")
            return redirect(url_for("auth.login"))

    # Actualizar el timestamp en cada request activo
    session["last_activity"] = ahora.isoformat()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Debe iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Permite el acceso únicamente a usuarios autenticados con rol Administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Debe iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('auth.login'))
        if not es_administrador():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def check_permission(permission_name):
    """Verifica si el usuario logueado tiene un permiso particular."""
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
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                flash('Debe iniciar sesión para acceder a esta página.', 'error')
                return redirect(url_for('auth.login'))
            if not check_permission(permission_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
