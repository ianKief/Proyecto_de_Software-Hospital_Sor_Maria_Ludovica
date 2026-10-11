from src.core.db import db
from src.core.sectors.models import Sector
from src.core.sectors.exceptions import SectorValidationError
from src.core.sectors.validators import validate_nombre, validate_descripcion, validate_deactivation

# ==========================================
# FUNCIONES CORE
# ==========================================

def get_sector_by_name(nombre: str) -> Sector | None:
    """Busca un sector por coincidencia exacta insensible a mayúsculas/minúsculas."""
    return Sector.query.filter(Sector.nombre.ilike(nombre.strip())).first()

def get_sector(sector_id: int) -> Sector | None:
    """Obtiene un sector por su ID."""
    return Sector.query.get(sector_id)

def list_sectors(
        page: int = 1, 
        per_page: int = 25, 
        sort_by: str = 'nombre', 
        order: str = 'asc',
        search_nombre: str = None,
        search_estado: str = None,
        search_jefe: str = None
    ):
    from src.core.users.models import User
    """
    Retorna un objeto Pagination con los sectores ordenados alfabéticamente.
    """
    query = Sector.query

    # Filtro por Nombre de Sector (insensible a mayúsculas/minúsculas)
    if search_nombre:
        query = query.filter(Sector.nombre.ilike(f'%{search_nombre}%'))

    # Filtro por Estado
    if search_estado in ['activo', 'inactivo']:
        is_active = True if search_estado == 'activo' else False
        query = query.filter(Sector.activo == is_active)

    # Filtro por Jefe de Servicio (Nombre o Apellido)
    if search_jefe:
        query = query.join(Sector.jefes_servicio).filter(
            (User.nombre.ilike(f'%{search_jefe}%')) | 
            (User.apellido.ilike(f'%{search_jefe}%'))
        )

    # Determinamos la columna por la cual ordenar
    if sort_by == 'created_at':
        sort_column = Sector.created_at
    else:
        sort_column = Sector.nombre  # Por defecto ordenamos por nombre

    # Determinamos la dirección (ascendente o descendente)
    if order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    return query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )

def create_sector(nombre: str, descripcion: str | None = None) -> Sector:
    """
    Crea y persiste un nuevo sector aplicando todas las reglas de negocio.
    """
    # Delegamos las validaciones (Para la creación, la descripción es obligatoria)
    nombre_limpio = validate_nombre(nombre)
    descripcion_limpia = validate_descripcion(descripcion, is_required=True)

    sector = Sector(
        nombre=nombre_limpio,
        descripcion=descripcion_limpia,
        activo=True,
    )
    db.session.add(sector)
    db.session.commit()
    return sector

def update_sector(sector_id: int, nombre: str = None, descripcion: str = None) -> Sector:
    """
    Actualiza los datos de un sector aplicando las reglas de negocio y validaciones.
    Conserva la descripción existente si se provee una cadena vacía o None.
    No modifica a los jefes de servicio.
    """
    sector = get_sector(sector_id)
    if not sector:
        raise SectorValidationError("El sector solicitado no existe.")

    # Si se envía un nombre, lo validamos (excluyendo el id actual de la unicidad) y lo asignamos
    if nombre and nombre.strip():
        sector.nombre = validate_nombre(nombre, exclude_sector_id=sector_id)

    # Si se envía una descripción, la validamos y la asignamos (si está vacía, no hace nada)
    if descripcion and descripcion.strip():
        sector.descripcion = validate_descripcion(descripcion, is_required=False)

    # La fecha de modificación (updated_at) se actualiza sola gracias a `onupdate` en el modelo.
    
    db.session.commit()
    return sector