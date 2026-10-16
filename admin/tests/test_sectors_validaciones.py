import pytest
from src.web import create_app
from src.core.db import db
from src.core.sectors.models import Sector
from src.core.personnel.models import Personal
from src.core.users.models import User
from src.core.auth.models import Role
from src.core.sectors.exceptions import (
    SectorValidationError, 
    SectorAlreadyExistsError, 
    SectorInactiveExistsError
)
from src.core.sectors.validators import (
    validate_nombre, 
    validate_descripcion, 
    validate_nombre_disponible,
    validate_deactivation,
    validate_deletion,
    validate_jefes_servicio
)
from src.core.personnel_types.models import PersonnelType
from src.core.menu_types.models import MenuType

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
def db_data(app):
    """Prepara datos básicos en la BD para probar validadores semánticos."""
    # Sectores
    sector_activo = Sector(nombre="Guardia", descripcion="Activo", activo=True)
    sector_inactivo = Sector(nombre="Archivo", descripcion="Inactivo", activo=False)
    
    # Roles
    rol_jefe = Role(name="Jefe de Servicio")
    rol_admin = Role(name="Administrador")
    
    db.session.add_all([sector_activo, sector_inactivo, rol_jefe, rol_admin])
    db.session.commit()
    
    # Usuarios
    jefe_libre = User(email="libre@test.com", nombre="Juan", apellido="Perez", dni="1", password="x", activo=True, role_id=rol_jefe.id)
    jefe_ocupado = User(email="ocupa@test.com", nombre="Ana", apellido="Gomez", dni="2", password="x", activo=True, role_id=rol_jefe.id, sector_id=sector_activo.id)
    no_jefe = User(email="admin@test.com", nombre="Luis", apellido="Sosa", dni="3", password="x", activo=True, role_id=rol_admin.id)
    
    db.session.add_all([jefe_libre, jefe_ocupado, no_jefe])
    db.session.commit()
    
    return {
        "sector_activo": sector_activo,
        "sector_inactivo": sector_inactivo,
        "jefe_libre": jefe_libre,
        "jefe_ocupado": jefe_ocupado,
        "no_jefe": no_jefe
    }

# ==========================================
# TESTS SINTÁCTICOS (No requieren estado complejo de BD)
# ==========================================

def test_validate_nombre_limpia_espacios():
    assert validate_nombre("   Pediatría   ") == "Pediatría"

def test_validate_nombre_vacio_falla():
    with pytest.raises(SectorValidationError) as exc:
        validate_nombre("")
    assert "vacío" in str(exc.value)

def test_validate_nombre_largo_falla():
    with pytest.raises(SectorValidationError) as exc:
        validate_nombre("A" * 256)
    assert "255" in str(exc.value)

def test_validate_descripcion_opcional_vacia():
    # Si is_required=False, devuelve None y no falla
    assert validate_descripcion("", is_required=False) is None

def test_validate_descripcion_obligatoria_vacia_falla():
    with pytest.raises(SectorValidationError) as exc:
        validate_descripcion("   ", is_required=True)
    assert "vacía" in str(exc.value)

def test_validate_descripcion_larga_falla():
    with pytest.raises(SectorValidationError) as exc:
        validate_descripcion("A" * 1001)
    assert "1000" in str(exc.value)

# ==========================================
# TESTS SEMÁNTICOS (Colisiones)
# ==========================================

def test_nombre_disponible_libre(db_data):
    # Un nombre que no existe devuelve None
    assert validate_nombre_disponible("Cardiología") is None

def test_nombre_disponible_colision_activa(db_data):
    with pytest.raises(SectorAlreadyExistsError):
        validate_nombre_disponible("Guardia")

def test_nombre_disponible_colision_inactiva_sin_confirmar(db_data):
    with pytest.raises(SectorInactiveExistsError):
        validate_nombre_disponible("Archivo", reactivacion_confirmada=False)

def test_nombre_disponible_colision_inactiva_con_confirmacion(db_data):
    # Devuelve el objeto del sector inactivo para ser reutilizado
    sector = validate_nombre_disponible("Archivo", reactivacion_confirmada=True)
    assert sector.id == db_data["sector_inactivo"].id

def test_nombre_disponible_ignorar_id(db_data):
    # Si ignoramos el ID del sector activo, no detecta colisión (útil para edición)
    sector_id = db_data["sector_activo"].id
    assert validate_nombre_disponible("Guardia", sector_id_ignorar=sector_id) is None

# ==========================================
# TESTS DE DEPENDENCIA (Bajas lógicas y físicas)
# ==========================================

def test_validate_deactivation_con_jefe(db_data):
    sector = db_data["sector_activo"]
    with pytest.raises(SectorValidationError) as exc:
        validate_deactivation(sector)
    assert "tiene jefes de servicio" in str(exc.value)

def test_validate_deletion_con_personal(db_data):
    sector = db_data["sector_activo"]
    # Vaciamos los jefes para probar el personal
    sector.jefes_servicio = []
    db.session.commit()
    
    # 1. Crear las dependencias obligatorias para el Personal
    tipo_personal = PersonnelType(nombre="Planta Permanente")
    tipo_menu = MenuType(nombre="General")
    db.session.add_all([tipo_personal, tipo_menu])
    db.session.commit()
    
    # 2. Agregamos el personal con sus campos obligatorios
    personal = Personal(
        dni="111", 
        nombre="X", 
        apellido="Y", 
        sector_id=sector.id,
        personnel_type_id=tipo_personal.id,
        menu_type_id=tipo_menu.id,
        activo=True
    )
    db.session.add(personal)
    db.session.commit()

    with pytest.raises(SectorValidationError) as exc:
        validate_deletion(sector)
    assert "tiene registros de personal" in str(exc.value)
# ==========================================
# TESTS DE JEFES DE SERVICIO
# ==========================================

def test_validate_jefes_lista_vacia():
    validos, errores = validate_jefes_servicio(None)
    assert validos == []
    assert errores == []

def test_validate_jefes_rol_incorrecto(db_data):
    validos, errores = validate_jefes_servicio([db_data["no_jefe"].id])
    assert not validos
    assert len(errores) == 1
    assert "no tiene el rol" in errores[0]

def test_validate_jefes_ocupado_en_otro_sector(db_data):
    validos, errores = validate_jefes_servicio([db_data["jefe_ocupado"].id], current_sector_id=999)
    assert not validos
    assert len(errores) == 1
    assert "ya está asignado a otro sector" in errores[0]

def test_validate_jefes_ocupado_en_mismo_sector(db_data):
    # Si ya es jefe del sector actual, lo ignora en silencio (no es error, pero tampoco "nuevo")
    sector_id = db_data["sector_activo"].id
    validos, errores = validate_jefes_servicio([db_data["jefe_ocupado"].id], current_sector_id=sector_id)
    assert not validos
    assert not errores

def test_validate_jefes_exito(db_data):
    validos, errores = validate_jefes_servicio([db_data["jefe_libre"].id])
    assert len(validos) == 1
    assert validos[0].id == db_data["jefe_libre"].id
    assert not errores