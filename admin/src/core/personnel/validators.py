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


def validate_csv_row(row_data: dict, dnis_procesados_archivo: set) -> dict:
    """
    Traduce los nombres de texto provenientes del CSV (tipo_personal, tipo_menu, sector)
    a sus IDs respectivos y ejecuta las validaciones de negocio.
    """
    dni = str(row_data.get("dni", "")).strip()

    # Validar duplicados dentro del mismo lote del CSV
    if dni in dnis_procesados_archivo:
        raise ValidationError(f"El DNI {dni} se encuentra duplicado en el mismo archivo CSV.")

    # Resolución de Tipo de Personal por nombre
    tp_nombre = str(row_data.get("tipo_personal", "")).strip()
    if not tp_nombre:
        raise ValidationError("El tipo de personal es obligatorio.")
    tp = PersonnelType.query.filter(PersonnelType.nombre.ilike(tp_nombre)).first()
    if not tp:
        raise ValidationError(f"El tipo de personal '{tp_nombre}' no existe en el sistema.")

    # Resolución de Tipo de Menú por nombre
    tm_nombre = str(row_data.get("tipo_menu", "")).strip()
    if not tm_nombre:
        raise ValidationError("El tipo de menú es obligatorio.")
    tm = MenuType.query.filter(MenuType.nombre.ilike(tm_nombre)).first()
    if not tm:
        raise ValidationError(f"El tipo de menú '{tm_nombre}' no existe en el sistema.")

    # Resolución de Sector por nombre (si fue especificado)
    sec_nombre = str(row_data.get("sector", "")).strip()
    sec_id = None
    if sec_nombre:
        sec = Sector.query.filter(Sector.nombre.ilike(sec_nombre)).first()
        if not sec:
            raise ValidationError(f"El sector '{sec_nombre}' no existe en el sistema.")
        sec_id = sec.id

    # Armamos el payload estándar y delegamos en validate_personnel_data
    payload = {
        "dni": dni,
        "nombre": row_data.get("nombre"),
        "apellido": row_data.get("apellido"),
        "personnel_type_id": tp.id,
        "menu_type_id": tm.id,
        "sector_id": sec_id,
        "activo": True,
    }

    return validate_personnel_data(payload)