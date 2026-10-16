import pytest
from src.web import create_app
from src.core.db import db
from src.core.sectors.models import Sector
from src.core.users.models import User
from src.core.auth.models import Role
from src.core.sectors.exceptions import SectorValidationError
from src.core.sectors import (
    get_sector_by_name, get_sector, list_sectors, create_sector, 
    update_sector, toggle_status, delete_sector, 
    add_jefes_to_sector, remove_jefe_from_sector
)

@pytest.fixture
def app(monkeypatch):
    """App con base de datos en memoria para testing."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def db_setup(app):
    """Prepara sectores, roles y usuarios para los tests."""
    sector_a = Sector(nombre="Guardia", descripcion="Sector A", activo=True)
    sector_b = Sector(nombre="Archivo", descripcion="Sector B", activo=False)
    
    rol_jefe = Role(name="Jefe de Servicio")
    db.session.add_all([sector_a, sector_b, rol_jefe])
    db.session.commit()
    
    # jefe_1 asignado a Guardia, jefe_2 libre
    jefe_1 = User(email="1@x.com", nombre="Juan", apellido="A", dni="1", password="x", activo=True, role_id=rol_jefe.id, sector_id=sector_a.id)
    jefe_2 = User(email="2@x.com", nombre="Ana", apellido="B", dni="2", password="x", activo=True, role_id=rol_jefe.id)
    db.session.add_all([jefe_1, jefe_2])
    db.session.commit()
    
    return {"sector_a": sector_a, "sector_b": sector_b, "jefe_1": jefe_1, "jefe_2": jefe_2}


# --- READ: get_sector y get_sector_by_name ---

def test_get_sector_by_name(db_setup):
    """Prueba búsqueda exacta e insensible a mayúsculas[cite: 7]."""
    assert get_sector_by_name("guardia").id == db_setup["sector_a"].id
    assert get_sector_by_name("  GUARDIA  ").id == db_setup["sector_a"].id
    assert get_sector_by_name("Inexistente") is None

def test_get_sector(db_setup):
    """Prueba búsqueda por ID[cite: 7]."""
    assert get_sector(db_setup["sector_a"].id).nombre == "Guardia"
    assert get_sector(999) is None


# --- LIST: list_sectors ---

def test_list_sectors_filtros(db_setup):
    """Prueba la paginación y el filtrado por estado y nombre[cite: 7]."""
    # Sin filtros, trae todos
    paginacion = list_sectors(page=1)
    assert paginacion.total == 2
    
    # Filtro inactivos
    pag_inactivos = list_sectors(page=1, search_estado="inactivo")
    assert pag_inactivos.total == 1
    assert pag_inactivos.items[0].nombre == "Archivo"


# --- CREATE & UPDATE ---

def test_create_sector_exito(app):
    """Prueba que create_sector guarde en DB[cite: 7]."""
    sector, advertencias = create_sector("Nuevo", "Desc")
    assert sector.id is not None
    assert get_sector_by_name("Nuevo") is not None

def test_update_sector_exito(db_setup):
    """Prueba actualización de campos básicos[cite: 7]."""
    sector_id = db_setup["sector_b"].id
    sector_actualizado, _ = update_sector(sector_id, nombre="Archivo Central", descripcion="Nueva desc")
    
    assert sector_actualizado.nombre == "Archivo Central"
    assert sector_actualizado.descripcion == "Nueva desc"


# --- JEFES DE SERVICIO ---

def test_add_jefes_to_sector(db_setup):
    """Añade un jefe a un sector existente[cite: 7]."""
    sector = db_setup["sector_a"]
    jefe_nuevo = db_setup["jefe_2"]
    
    sector_actualizado, adv = add_jefes_to_sector(sector.id, [jefe_nuevo.id])
    assert jefe_nuevo in sector_actualizado.jefes_servicio

def test_remove_jefe_from_sector(db_setup):
    """Desvincula un jefe y verifica que SQLAlchemy limpie la relación[cite: 7]."""
    sector = db_setup["sector_a"]
    jefe = db_setup["jefe_1"]
    
    remove_jefe_from_sector(sector.id, jefe.id)
    
    db.session.refresh(sector)
    db.session.refresh(jefe)
    assert jefe not in sector.jefes_servicio
    assert jefe.sector_id is None


# --- ESTADO Y ELIMINACIÓN ---

def test_toggle_status_exito(db_setup):
    """Inactivo a activo siempre funciona[cite: 7]. Activo a inactivo funciona si no hay dependencias."""
    sector_b = db_setup["sector_b"] # Inactivo
    
    # Activar
    activado = toggle_status(sector_b.id)
    assert activado.activo is True

def test_delete_sector_fisico(app):
    """Si no tiene dependencias, delete_sector lo borra físicamente[cite: 7]."""
    sector = Sector(nombre="Limpio", descripcion="X", activo=True)
    db.session.add(sector)
    db.session.commit()
    
    sector_id = sector.id
    eliminado, msj = delete_sector(sector_id)
    
    assert eliminado is True
    assert get_sector(sector_id) is None

def test_delete_sector_baja_logica(db_setup):
    """Si tiene jefes, la eliminación física falla y hace baja lógica (activo = False)[cite: 7]."""
    sector = db_setup["sector_a"]
    assert sector.activo is True
    
    eliminado, msj = delete_sector(sector.id)
    
    # Fue baja lógica
    assert eliminado is False
    assert "desactivado" in msj
    
    # El registro sigue existiendo pero inactivo
    db.session.refresh(sector)
    assert sector.activo is False

def test_delete_sector_inactivo_con_dependencias(db_setup):
    """Si ya está inactivo y tiene dependencias, lanza error[cite: 7]."""
    sector = db_setup["sector_a"]
    sector.activo = False # Lo forzamos a inactivo
    db.session.commit()
    
    # Intentar borrarlo levantará excepción porque tiene al jefe_1 asignado
    with pytest.raises(SectorValidationError) as exc:
        delete_sector(sector.id)
        
    assert "ya se encuentra inactivo" in str(exc.value)