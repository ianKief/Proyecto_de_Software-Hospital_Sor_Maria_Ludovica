from src.core.db import db
from src.core.quotas.models import Cupo
from src.core.sectors.models import Sector
from src.core.food_types.models import FoodType
from src.core.quotas.validators import validate_quota_data, ValidationError


def get_quota_by_id(quota_id: int) -> Cupo | None:
    """Retorna un cupo por su identificador primario."""
    return Cupo.query.get(quota_id)


def list_food_types():
    """Retorna la lista de todos los tipos de comida disponibles."""
    return FoodType.query.order_by(FoodType.nombre.asc()).all()


def list_active_sectors():
    """Retorna solo sectores activos para la asignación de cupos."""
    return Sector.query.filter_by(activo=True).order_by(Sector.nombre.asc()).all()


def list_quotas(sector_id=None, tipo_comida_id=None, order="asc"):
    """
    Consulta cupos con filtros opcionales de sector y tipo de comida,
    ordenados por el nombre del sector.
    """
    query = Cupo.query.join(Sector).join(FoodType).filter(Sector.activo.is_(True))

    if sector_id:
        query = query.filter(Cupo.sector_id == sector_id)

    if tipo_comida_id:
        query = query.filter(Cupo.tipo_comida_id == tipo_comida_id)

    if order == "desc":
        query = query.order_by(Sector.nombre.desc(), FoodType.nombre.asc())
    else:
        query = query.order_by(Sector.nombre.asc(), FoodType.nombre.asc())

    return query

def create_quota(data: dict) -> Cupo:
    """Valida los datos y persiste un nuevo cupo."""
    validated = validate_quota_data(data)
    cupo = Cupo(**validated)
    db.session.add(cupo)
    db.session.commit()
    return cupo


def update_quota(quota_id: int, data: dict) -> Cupo:
    """Valida y modifica un cupo existente."""
    cupo = get_quota_by_id(quota_id)
    if not cupo:
        raise ValidationError("El cupo a editar no existe.")

    validated = validate_quota_data(data, current_quota_id=quota_id)
    for key, value in validated.items():
        setattr(cupo, key, value)

    db.session.commit()
    return cupo


def delete_quota(quota_id: int) -> bool:
    """Elimina físicamente un cupo."""
    cupo = get_quota_by_id(quota_id)
    if not cupo:
        raise ValidationError("El cupo a eliminar no existe.")

    db.session.delete(cupo)
    db.session.commit()
    return True