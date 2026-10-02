from functools import wraps
from flask import session, redirect, url_for, flash, abort
from src.core.users.models import User

def is_authenticated():
    return session.get("user") is not None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Debe iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def check_permission(permission_name):
    """Verifica si el usuario logueado tiene un permiso particular."""
    if not is_authenticated():
        return False
        
    user = User.query.get(session.get("user_id"))
    if not user or not user.activo:
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
