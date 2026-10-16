from src.core.quotas.models import Cupo
from src.core.sectors.models import Sector
from src.core.food_types.models import FoodType


class ValidationError(Exception):
    """Excepción para errores en las reglas de negocio de Cupos."""
    pass


def validate_quota_data(data: dict, current_quota_id: int | None = None) -> dict:
    """
    Valida las reglas de negocio para la carga y edición de cupos:
    - Campos requeridos presentes.
    - Cantidad mayor que cero.
    - Existencia y estado activo del sector.
    - Existencia del tipo de comida.
    - Unicidad: no pueden coexistir dos cupos para el mismo sector y tipo de comida.
    """
    raw_sector_id = data.get("sector_id")
    raw_tipo_comida_id = data.get("tipo_comida_id")
    raw_cantidad = data.get("cantidad")

    # 1. Validar Sector
    if not raw_sector_id:
        raise ValidationError("Debe seleccionar un sector.")
    try:
        sector_id = int(raw_sector_id)
    except (ValueError, TypeError):
        raise ValidationError("El sector seleccionado no es válido.")

    sector = Sector.query.get(sector_id)
    if not sector:
        raise ValidationError("El sector seleccionado no existe.")
    if not sector.activo:
        raise ValidationError("No se puede asignar un cupo a un sector inactivo.")

    # 2. Validar Tipo de Comida
    if not raw_tipo_comida_id:
        raise ValidationError("Debe seleccionar un tipo de comida.")
    try:
        tipo_comida_id = int(raw_tipo_comida_id)
    except (ValueError, TypeError):
        raise ValidationError("El tipo de comida no es válido.")

    tipo_comida = FoodType.query.get(tipo_comida_id)
    if not tipo_comida:
        raise ValidationError("El tipo de comida seleccionado no existe.")

    # 3. Validar Cantidad
    if raw_cantidad is None or str(raw_cantidad).strip() == "":
        raise ValidationError("La cantidad de comensales es obligatoria.")
    try:
        cantidad = int(raw_cantidad)
    except (ValueError, TypeError):
        raise ValidationError("La cantidad debe ser un número entero.")

    if cantidad <= 0:
        raise ValidationError("La cantidad de comensales debe ser estrictamente mayor que cero.")

    # 4. Validar Unicidad (mismo sector y mismo tipo de comida)
    query = Cupo.query.filter_by(sector_id=sector_id, tipo_comida_id=tipo_comida_id)
    if current_quota_id:
        query = query.filter(Cupo.id != current_quota_id)

    if query.first():
        raise ValidationError(
            f"Ya existe un cupo definido para el sector '{sector.nombre}' y el tipo de comida '{tipo_comida.nombre}'."
        )

    return {
        "sector_id": sector_id,
        "tipo_comida_id": tipo_comida_id,
        "cantidad": cantidad,
    }