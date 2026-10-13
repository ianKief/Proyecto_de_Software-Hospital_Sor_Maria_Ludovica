from src.core.users.models import User
from src.core.auth.models import Role

def get_jefes_disponibles() -> list[User]:
    """
    Retorna la lista de usuarios activos que tienen el rol 'Jefe de Servicio' 
    y que actualmente no están asignados a ningún sector.
    """
    return User.query.join(Role).filter(
        User.sector_id == None, 
        User.activo == True,
        Role.name == 'Jefe de Servicio'
    ).all()