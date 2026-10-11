from src.core.sectors.models import Sector
from src.core.sectors.exceptions import SectorValidationError, SectorAlreadyExistsError
from src.core.personnel.models import Personnel

MAX_NOMBRE_LENGTH = 255
MAX_DESCRIPCION_LENGTH = 1000

# ==========================================
# FUNCIONES DE VALIDACIÓN EXTRAÍDAS
# ==========================================

def validate_nombre(nombre: str, exclude_sector_id: int | None = None) -> str:
    """
    Valida y limpia el nombre del sector.
    Comprueba que no esté vacío, respete la longitud máxima y sea único.
    """
    if not nombre or not nombre.strip():
        raise SectorValidationError("El nombre del sector no puede estar vacío.")

    nombre_limpio = nombre.strip()

    if len(nombre_limpio) > MAX_NOMBRE_LENGTH:
        raise SectorValidationError(
            f"El nombre no puede superar los {MAX_NOMBRE_LENGTH} caracteres."
        )

    # Chequeo de unicidad (case-insensitive)
    query = Sector.query.filter(Sector.nombre.ilike(nombre_limpio))
    
    # Si estamos actualizando, excluimos el sector actual de la búsqueda
    if exclude_sector_id is not None:
        query = query.filter(Sector.id != exclude_sector_id)
        
    if query.first() is not None:
        raise SectorAlreadyExistsError(
            f"Ya existe un sector registrado con el nombre '{nombre_limpio}'."
        )

    return nombre_limpio


def validate_descripcion(descripcion: str | None, is_required: bool = False) -> str | None:
    """
    Valida y limpia la descripción del sector.
    Comprueba la obligatoriedad (si corresponde) y la longitud máxima.
    """
    if not descripcion or not descripcion.strip():
        if is_required:
            raise SectorValidationError("La descripción del sector no puede estar vacía.")
        return None

    descripcion_limpia = descripcion.strip()

    if len(descripcion_limpia) > MAX_DESCRIPCION_LENGTH:
        raise SectorValidationError(
            f"La descripción no puede superar los {MAX_DESCRIPCION_LENGTH} caracteres."
        )

    return descripcion_limpia

def validate_deactivation(sector) -> None:
    """
    Valida si un sector cumple con las reglas de negocio para ser desactivado.
    No debe tener jefes de servicio activos ni personal asignado.
    """
    # 1. Validar que no tenga jefes de servicio activos
    jefes_activos = [jefe for jefe in sector.jefes_servicio if getattr(jefe, 'activo', True)]
    if jefes_activos:
        raise SectorValidationError(
            "No se puede desactivar el sector porque tiene jefes de servicio activos asignados."
        )
        
    # 2. Validar que no tenga personal asignado
    personal_asignado = Personnel.query.filter_by(sector_id=sector.id).first()
    if personal_asignado:
        raise SectorValidationError(
            "No se puede desactivar el sector porque tiene personal del hospital asignado."
        )