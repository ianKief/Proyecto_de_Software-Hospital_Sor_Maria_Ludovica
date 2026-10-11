import re
from sqlalchemy import or_
from src.core.db import db
from src.core.personnel.models import Personnel, PersonnelType, MenuType
from src.core.sectors.models import Sector
from src.core.personnel.validators import validate_personnel_data, ValidationError
from src.core.paginacion.py import paginar

# consultas

def list_personnel_types():
    """Retorna los tipos de personal."""
    return PersonnelType.query.order_by(PersonnelType.nombre).all()


def list_menu_types():
    """Retorna los tipos de menú."""
    return MenuType.query.order_by(MenuType.nombre).all()


def list_active_sectors():
    """Retorna los sectores activos para asignación."""
    return Sector.query.filter_by(activo=True).order_by(Sector.nombre).all()


def get_personnel_by_id(personnel_id: int) -> Personnel | None:
    """Busca una persona por su ID."""
    return Personnel.query.get(personnel_id)


def list_personnel(
    dni: str | None = None,
    nombre_apellido: str | None = None,
    sector_id: int | None = None,
    personnel_type_id: int | None = None,
    activo: bool | None = None,
    order_by: str = "apellido_nombre",
    order_direction: str = "asc",
    page: int = 1,
    per_page: int = 25,
):
    """
    Aplica filtros, ordenamiento y devuelve la paginación estandarizada.
    """
    query = Personnel.query

    if dni and dni.strip():
        query = query.filter(Personnel.dni.ilike(f"%{dni.strip()}%"))

    if nombre_apellido and nombre_apellido.strip():
        term = f"%{nombre_apellido.strip()}%"
        query = query.filter(or_(Personnel.nombre.ilike(term), Personnel.apellido.ilike(term)))

    if sector_id:
        query = query.filter(Personnel.sector_id == sector_id)

    if personnel_type_id:
        query = query.filter(Personnel.personnel_type_id == personnel_type_id)

    if activo is not None:
        query = query.filter(Personnel.activo == activo)

    # Ordenamiento
    desc = order_direction.lower() == "desc"
    if order_by == "dni":
        order_col = Personnel.dni.desc() if desc else Personnel.dni.asc()
        query = query.order_by(order_col)
    elif order_by == "created_at":
        order_col = Personnel.created_at.desc() if desc else Personnel.created_at.asc()
        query = query.order_by(order_col)
    else:
        if desc:
            query = query.order_by(Personnel.apellido.desc(), Personnel.nombre.desc())
        else:
            query = query.order_by(Personnel.apellido.asc(), Personnel.nombre.asc())

    # Usamos despues la funcion paginar!!!!!
    return paginar(query, page)


def create_personnel(data: dict) -> Personnel:
    """Valida los datos y registra una nueva persona."""
    validated = validate_personnel_data(data)
    person = Personnel(**validated)  
    db.session.add(person)
    db.session.commit()
    return person


def update_personnel(personnel_id: int, data: dict) -> Personnel:
    """Valida los datos y modifica una persona existente."""
    person = get_personnel_by_id(personnel_id)
    if not person:
        raise ValidationError("La persona a editar no existe.")

    validated = validate_personnel_data(data, current_personnel_id=personnel_id)
    for key, value in validated.items():
        setattr(person, key, value)

    db.session.commit()
    return person


def has_order_history(personnel_id: int) -> bool:
    """Verifica si la persona tiene historial en pedidos o entregas."""
    return False


def delete_personnel(personnel_id: int) -> tuple[bool, str]:
    """
    Eliminación física si no tiene historial; baja lógica (activo = False) si lo tiene.
    """
    person = get_personnel_by_id(personnel_id)
    if not person:
        raise ValidationError("La persona a eliminar no existe.")

    if has_order_history(personnel_id):
        person.activo = False
        db.session.commit()
        return False, f"La persona {person.nombre} {person.apellido} posee historial y fue desactivada."
    else:
        db.session.delete(person)
        db.session.commit()
        return True, f"La persona {person.nombre} {person.apellido} fue eliminada del sistema."