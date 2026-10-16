import re
from src.core.personnel.models import Personnel
from src.core.sectors.models import Sector
from src.core.personnel_types.models import PersonnelType
from src.core.menu_types.models import MenuType

class ValidationError(Exception):
    """Excepción para errores de validación de negocio."""
    pass


def validate_dni(dni: str, current_personnel_id: int | None = None) -> str:
    """Valida formato numérico y unicidad de DNI."""
    if not dni or not str(dni).strip():
        raise ValidationError("El DNI es obligatorio.")

    dni_cleaned = str(dni).strip()
    if not re.fullmatch(r"^\d{7,9}$", dni_cleaned):
        raise ValidationError("El DNI debe contener entre 7 y 9 números sin puntos ni espacios.")

    existing = Personnel.query.filter_by(dni=dni_cleaned).first()
    if existing and (current_personnel_id is None or existing.id != current_personnel_id):
        raise ValidationError(f"Ya existe una persona registrada con el DNI {dni_cleaned}.")

    return dni_cleaned


def validate_personnel_data(data: dict, current_personnel_id: int | None = None) -> dict:
    """Valida los campos obligatorios, sector y menú según las reglas de negocio."""
    nombre = str(data.get("nombre", "")).strip()
    apellido = str(data.get("apellido", "")).strip()

    if not nombre:
        raise ValidationError("El nombre es obligatorio.")
    if len(nombre) > 100:
        raise ValidationError("El nombre no puede superar los 100 caracteres.")

    if not apellido:
        raise ValidationError("El apellido es obligatorio.")
    if len(apellido) > 100:
        raise ValidationError("El apellido no puede superar los 100 caracteres.")

    dni_cleaned = validate_dni(data.get("dni"), current_personnel_id)

    personnel_type_id = data.get("personnel_type_id")
    if not personnel_type_id:
        raise ValidationError("Debe seleccionar un tipo de personal.")

    personnel_type = PersonnelType.query.get(personnel_type_id)
    if not personnel_type:
        raise ValidationError("El tipo de personal seleccionado no existe.")

    raw_sector_id = data.get("sector_id")
    sector_id = None

    if personnel_type.requiere_sector:
        if not raw_sector_id:
            raise ValidationError(f"El tipo de personal '{personnel_type.nombre}' requiere un sector obligatorio.")
        sector = Sector.query.get(raw_sector_id)
        if not sector:
            raise ValidationError("El sector seleccionado no existe.")
        if not sector.activo:
            raise ValidationError("No se puede asignar un sector inactivo.")
        sector_id = sector.id
    else:
        sector_id = None

    menu_type_id = data.get("menu_type_id")
    if not menu_type_id:
        raise ValidationError("Debe seleccionar un tipo de menú predeterminado.")

    menu_type = MenuType.query.get(menu_type_id)
    if not menu_type:
        raise ValidationError("El tipo de menú seleccionado no existe.")

    activo = data.get("activo", True)
    if isinstance(activo, str):
        activo = activo.lower() in ["true", "1", "on", "yes", "si"]

    return {
        "dni": dni_cleaned,
        "nombre": nombre,
        "apellido": apellido,
        "personnel_type_id": personnel_type.id,
        "sector_id": sector_id,
        "menu_type_id": menu_type.id,
        "activo": bool(activo),
    }