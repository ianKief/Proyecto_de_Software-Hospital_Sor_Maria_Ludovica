from src.core.users.models import User


def list_users():
    usuarios = User.query.order_by(
        User.apellido,
        User.nombre,
    ).all()

    return [
        {
            "email": usuario.email,
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "dni": usuario.dni,
            "activo": usuario.activo,
            "rol": usuario.role.name if usuario.role else "",
        }
        for usuario in usuarios
    ]