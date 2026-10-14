from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app

SALT_ACTIVACION = "account-activation-salt"
SALT_MAGIC_LOGIN = "magic-login-salt"

def _get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

def generar_token_activacion(user_id):
    """Genera un token firmado para la activación de cuenta y configuración inicial de contraseña."""
    s = _get_serializer()
    return s.dumps(user_id, salt=SALT_ACTIVACION)

def verificar_token_activacion(token, max_age=86400):
    """Verifica el token de activación (válido por 24 horas por defecto).
    
    Devuelve el user_id si es válido, o None si expiró o es inválido.
    """
    s = _get_serializer()
    try:
        user_id = s.loads(token, salt=SALT_ACTIVACION, max_age=max_age)
        return user_id
    except (SignatureExpired, BadSignature):
        return None

def generar_token_magic_login(user_id):
    """Genera un token firmado para inicio de sesión sin contraseña (Magic Link)."""
    s = _get_serializer()
    return s.dumps(user_id, salt=SALT_MAGIC_LOGIN)

def verificar_token_magic_login(token, max_age=900):
    """Verifica el token de magic login (válido por 15 minutos por defecto).
    
    Devuelve el user_id si es válido, o None si expiró o es inválido.
    """
    s = _get_serializer()
    try:
        user_id = s.loads(token, salt=SALT_MAGIC_LOGIN, max_age=max_age)
        return user_id
    except (SignatureExpired, BadSignature):
        return None
