import bcrypt

def autenticar_usuario(email, password):
    """Verifica las credenciales de un usuario para inicio de sesión.

    Devuelve una tupla (user, error):
        - (user, None) si las credenciales son válidas y el usuario está activo.
        - (None, "desactivado") si el usuario existe pero su cuenta está inactiva.
        - (None, "credenciales_invalidas") si el usuario no existe o la contraseña no coincide.
    """
    from src.core.users.models import User
    if not email or not password:
        return None, "credenciales_invalidas"

    user = User.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        if not user.activo:
            return None, "desactivado"
        return user, None

    return None, "credenciales_invalidas"
