from src.core.db import db
from src.core.sectors.models import Sector
from src.core.sectors.exceptions import SectorValidationError, SectorInactiveExistsError
from src.core.sectors.validators import (
    validate_nombre, 
    validate_descripcion, 
    validate_deactivation,
    validate_deletion,
    validate_jefes_servicio,
    validate_nombre_disponible
    )
from src.core.paginacion import paginar

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
        sort_by: str = 'nombre', 
        order: str = 'asc',
        search_nombre: str = None,
        search_estado: str = None,
        search_jefe: str = None
    ):
    """
    Retorna un objeto Pagination con los sectores ordenados alfabéticamente.
    """
    from src.core.users.models import User
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

    return paginar(query, page)

def create_sector(nombre: str, descripcion: str | None = None, jefes_ids: list[int] = None, reactivar: bool = False) -> tuple[Sector, list[str]]:
    nombre_limpio = validate_nombre(nombre)
    descripcion_limpia = validate_descripcion(descripcion, is_required=True)
    jefes_validados, advertencias_jefes = validate_jefes_servicio(jefes_ids)

    sector_inactivo = validate_nombre_disponible(
        nombre_limpio=nombre_limpio, 
        reactivacion_confirmada=reactivar
    )

    if sector_inactivo:
        # Modo Reactivación: el validador nos entregó el sector inactivo
        sector_inactivo.activo = True
        sector_inactivo.descripcion = descripcion_limpia
        sector_inactivo.jefes_servicio = jefes_validados
        sector = sector_inactivo
        advertencias_jefes.append(f"El sector '{nombre_limpio}' fue reactivado exitosamente con los nuevos datos.")
    else:
        # Modo Creación Limpia: el validador nos dijo que el nombre es totalmente nuevo
        sector = Sector(
            nombre=nombre_limpio,
            descripcion=descripcion_limpia,
            activo=True,
            jefes_servicio=jefes_validados
        )
        db.session.add(sector)
        
    db.session.commit()
    return sector, advertencias_jefes


def update_sector(sector_id: int, nombre: str = None, descripcion: str = None, jefes_ids: list[int] = None) -> tuple[Sector, list[str]]:
    """
    Actualiza los datos de un sector aplicando las reglas de negocio y validaciones.
    Conserva la descripción existente si se provee una cadena vacía o None.
    Suma nuevos jefes de servicio a los ya existentes (no los sobrescribe).
    """
    sector = get_sector(sector_id)
    if not sector:
        raise SectorValidationError("El sector solicitado no existe.")

    # Si se envía un nombre, lo validamos (excluyendo el id actual de la unicidad) y lo asignamos
    if nombre and nombre.strip():
        nombre_limpio = validate_nombre(nombre, exclude_sector_id=sector_id)
        validate_nombre_disponible(nombre_limpio, sector_id_ignorar=sector_id)
        sector.nombre = nombre_limpio

    # Si se envía una descripción, la validamos y la asignamos
    if descripcion and descripcion.strip():
        sector.descripcion = validate_descripcion(descripcion, is_required=False)

    # Validamos los jefes pasándole el ID actual
    jefes_validados, advertencias = validate_jefes_servicio(jefes_ids, current_sector_id=sector.id)

    # Agregamos solo los nuevos jefes válidos que no estén ya asignados al sector
    if jefes_ids is not None:
        jefes_actuales = sector.jefes_servicio
        for nuevo_jefe in jefes_validados:
            if nuevo_jefe not in jefes_actuales:
                sector.jefes_servicio.append(nuevo_jefe)

    # La fecha de modificación (updated_at) se actualiza sola gracias a `onupdate` en el modelo.
    
    db.session.commit()
    
    return sector, advertencias

def toggle_status(sector_id: int) -> Sector:
    """
    Activa o desactiva un sector.
    Si se intenta desactivar, delega la validación de dependencias al validator.
    """
    sector = get_sector(sector_id)
    if not sector:
        raise SectorValidationError("El sector solicitado no existe.")

    if sector.activo:
        # Si está activo y lo queremos desactivar, ejecutamos las reglas de validación
        validate_deactivation(sector)
        sector.activo = False
    else:
        # Si estaba inactivo, lo activamos sin restricciones
        sector.activo = True

    db.session.commit()
    return sector

def delete_sector(sector_id: int) -> tuple[bool, str]:
    """
    Intenta eliminar un sector físicamente de la base de datos.
    Si el sector tiene dependencias (personal, pedidos, etc.), se captura 
    la excepción de validación y se procede a una baja lógica (desactivación).
    
    Retorna:
        Una tupla (eliminado_fisicamente: bool, mensaje_resultado: str)
    """
    sector = get_sector(sector_id)
    if not sector:
        raise SectorValidationError("El sector solicitado no existe o ya fue eliminado.")

    try:
        # Intentamos validar si se puede eliminar físicamente
        validate_deletion(sector)
        
        # Si no saltaron errores, lo borramos de verdad
        nombre = sector.nombre
        db.session.delete(sector)
        db.session.commit()
        return True, f"El sector '{nombre}' fue eliminado permanentemente del sistema."

    except SectorValidationError as e:
        # Si la validación falla (ej: "tiene registros de personal asociados")
        motivo = str(e)
        
        if sector.activo:
            # Hacemos la baja lógica y avisamos
            sector.activo = False
            db.session.commit()
            return False, f"El sector '{sector.nombre}' no pudo ser eliminado de forma permanente porque {motivo}. En su lugar, ha sido desactivado."
        else:
            # Si ya estaba inactivo y tampoco se puede borrar
            raise SectorValidationError(
                f"El sector ya se encuentra inactivo, pero no puede ser eliminado de forma permanente porque {motivo}."
            )

def add_jefes_to_sector(sector_id: int, jefes_ids: list[int]) -> tuple[Sector, list[str]]:
    """Suma nuevos jefes a un sector existente."""
    sector = get_sector(sector_id)
    if not sector:
        raise SectorValidationError("El sector solicitado no existe.")
        
    jefes_validados, advertencias = validate_jefes_servicio(jefes_ids, current_sector_id=sector.id)
    
    if jefes_ids:
        jefes_actuales = sector.jefes_servicio
        for nuevo_jefe in jefes_validados:
            if nuevo_jefe not in jefes_actuales:
                sector.jefes_servicio.append(nuevo_jefe)
                
    db.session.commit()
    return sector, advertencias

def remove_jefe_from_sector(sector_id: int, jefe_id: int):
    """Desvincula un jefe específico de un sector."""
    from src.core.users.models import User
    sector = get_sector(sector_id)
    if not sector:
        raise SectorValidationError("El sector solicitado no existe.")
        
    jefe = User.query.get(jefe_id)
    if jefe and jefe in sector.jefes_servicio:
        sector.jefes_servicio.remove(jefe) # SQLAlchemy setea el sector_id a None automáticamente
        db.session.commit()