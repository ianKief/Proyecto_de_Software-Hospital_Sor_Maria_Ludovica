from src.core.db import db
from src.core.sectors.models import Sector
from src.core.sectors.exceptions import SectorValidationError, SectorAlreadyExistsError

MAX_NOMBRE_LENGTH = 255
MAX_DESCRIPCION_LENGTH = 1000


def get_sector_by_name(nombre: str) -> Sector | None:
    """Busca un sector por coincidencia exacta insensible a mayúsculas/minúsculas."""
    return Sector.query.filter(Sector.nombre.ilike(nombre.strip())).first()


def create_sector(nombre: str, descripcion: str | None = None) -> Sector:
    """
    Crea y persiste un nuevo sector aplicando todas las reglas de negocio.
    
    Reglas de negocio:
    - El nombre es obligatorio y no puede ser solo espacios en blanco.
    - El nombre no debe superar los 255 caracteres.
    - La descripción no debe superar los 1000 caracteres.
    - El nombre debe ser único en el sistema (case-insensitive).
    """
    if not nombre or not nombre.strip():
        raise SectorValidationError("El nombre del sector no puede estar vacío.")

    if not descripcion or not descripcion.strip():
            raise SectorValidationError("La descripción del sector no puede estar vacío.")
    

    nombre_limpio = nombre.strip()

    if len(nombre_limpio) > MAX_NOMBRE_LENGTH:
        raise SectorValidationError(
            f"El nombre no puede superar los {MAX_NOMBRE_LENGTH} caracteres."
        )

    descripcion_limpia = descripcion.strip() if descripcion else None
    if descripcion_limpia and len(descripcion_limpia) > MAX_DESCRIPCION_LENGTH:
        raise SectorValidationError(
            f"La descripción no puede superar los {MAX_DESCRIPCION_LENGTH} caracteres."
        )

    # Validación de unicidad en la capa de negocio
    if get_sector_by_name(nombre_limpio) is not None:
        raise SectorAlreadyExistsError(
            f"Ya existe un sector registrado con el nombre '{nombre_limpio}'."
        )

    sector = Sector(
        nombre=nombre_limpio,
        descripcion=descripcion_limpia,
        activo=True,
    )
    db.session.add(sector)
    db.session.commit()
    return sector