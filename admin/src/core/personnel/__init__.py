from datetime import date, timedelta
import re
from sqlalchemy import or_

from src.core.db import db
from src.core.paginacion import paginar
from src.core.personnel.models import Personnel
from src.core.personnel.validators import validate_personnel_data, ValidationError

# Imports según la nueva estructura de carpetas de tu equipo:
from src.core.personnel_types.models import PersonnelType
from src.core.menu_types.models import MenuType
from src.core.sectors.models import Sector

# Intentamos importar AsignacionSector y Pedido si existen en sus respectivos módulos
try:
    from src.core.personnel.models import AsignacionSector
except ImportError:
    AsignacionSector = None

try:
    from src.core.pedidos.models import Pedido
except ImportError:
    Pedido = None


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
    return db.session.get(Personnel, personnel_id)


def list_personnel(
    page: int = 1,
    dni: str | None = None,
    nombre_apellido: str | None = None,
    sector_id: int | None = None,
    personnel_type_id: int | None = None,
    activo: bool | None = None,
    order_by: str = "apellido_nombre",
    order_direction: str = "asc",
):
    """
    Aplica filtros, ordenamiento y devuelve la paginación estandarizada con paginar().
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
    desc = str(order_direction).lower() == "desc"
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
    """Verifica si la persona tiene historial en pedidos."""
    if Pedido:
        # Si la tabla pedidos ya tiene referencia a personal_id
        if hasattr(Pedido, "personal_id"):
            return Pedido.query.filter_by(personal_id=personnel_id).first() is not None
        elif hasattr(Pedido, "personnel_id"):
            return Pedido.query.filter_by(personnel_id=personnel_id).first() is not None
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


def cambiar_asignacion_sector(personal_id: int, sector_id: int | None, fecha_desde=None):
    """Cambia el sector de una persona conservando su historial."""
    if fecha_desde is None:
        fecha_desde = date.today()

    personal = get_personnel_by_id(personal_id)
    if personal is None:
        raise LookupError("Personal no encontrado")

    nuevo_sector = None
    if sector_id is not None:
        nuevo_sector = db.session.get(Sector, sector_id)
        if nuevo_sector is None:
            raise LookupError("Sector no encontrado")
        if not nuevo_sector.activo:
            raise ValueError("No se puede asignar personal a un sector inactivo")

    if AsignacionSector:
        asignacion_actual = (
            AsignacionSector.query
            .filter_by(
                personal_id=personal.id,
                fecha_hasta=None,
            )
            .first()
        )

        if asignacion_actual is not None and asignacion_actual.sector_id == sector_id:
            return personal

        try:
            if asignacion_actual is not None:
                if fecha_desde < asignacion_actual.fecha_desde:
                    raise ValueError(
                        "La fecha del cambio no puede ser anterior "
                        "al inicio de la asignación vigente"
                    )

                asignacion_actual.fecha_hasta = max(
                    fecha_desde - timedelta(days=1),
                    asignacion_actual.fecha_desde,
                )

            personal.sector_id = sector_id

            if nuevo_sector is not None:
                nueva_asignacion = AsignacionSector(
                    personal_id=personal.id,
                    sector_id=nuevo_sector.id,
                    fecha_desde=fecha_desde,
                )
                db.session.add(nueva_asignacion)

            db.session.commit()
            return personal

        except Exception:
            db.session.rollback()
            raise
    else:
        personal.sector_id = sector_id
        db.session.commit()
        return personal