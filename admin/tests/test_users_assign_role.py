import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role
from src.core.users.models import User
from src.core.sectors.models import Sector
from src.core.users import assign_role
from src.core.users.exceptions import UserNotFoundError, RoleNotFoundError

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
def datos(app):
    """Prepara roles, un sector y usuarios para las pruebas."""
    # 1. Crear roles
    rol_jefe = Role(name="Jefe de Servicio")
    rol_admin = Role(name="Administrador")
    rol_comedor = Role(name="Sector Comedor")
    db.session.add_all([rol_jefe, rol_admin, rol_comedor])
    db.session.commit()

    # 2. Crear sector
    sector_guardia = Sector(nombre="Guardia", descripcion="Test", activo=True)
    db.session.add(sector_guardia)
    db.session.commit()

    # 3. Crear usuarios
    # House es Jefe de Servicio y está asignado a la Guardia
    house = User(
        email="house@hospital.com",
        nombre="Gregory",
        apellido="House",
        dni="112233",
        password="hash",
        activo=True,
        role_id=rol_jefe.id,
        sector_id=sector_guardia.id
    )
    
    # Ana es de Sector Comedor y no tiene sector_id asignado
    ana = User(
        email="ana@hospital.com",
        nombre="Ana",
        apellido="Gómez",
        dni="445566",
        password="hash",
        activo=True,
        role_id=rol_comedor.id,
        sector_id=None
    )
    
    db.session.add_all([house, ana])
    db.session.commit()

    return {
        "rol_jefe": rol_jefe,
        "rol_admin": rol_admin,
        "rol_comedor": rol_comedor,
        "sector_guardia": sector_guardia,
        "jefe_house": house,
        "empleada_ana": ana
    }

def test_asignar_rol_exitoso(datos):
    """Cambiar el rol a un usuario normal funciona correctamente."""
    ana = datos["empleada_ana"]
    rol_admin = datos["rol_admin"]

    usuario_actualizado = assign_role(ana.id, rol_admin.id)

    assert usuario_actualizado.role_id == rol_admin.id
    assert usuario_actualizado.role.name == "Administrador"

def test_asignar_mismo_rol_no_hace_nada(datos):
    """Si se asigna el rol que ya tiene, la función retorna sin problemas."""
    ana = datos["empleada_ana"]
    rol_comedor = datos["rol_comedor"]

    # El rol original es Sector Comedor
    usuario_actualizado = assign_role(ana.id, rol_comedor.id)

    assert usuario_actualizado.role_id == rol_comedor.id

def test_jefe_de_servicio_pierde_sector_al_cambiar_rol(datos):
    """Regla de negocio: Si deja de ser Jefe de Servicio, sector_id debe quedar en None."""
    house = datos["jefe_house"]
    rol_admin = datos["rol_admin"]

    # Comprobamos estado inicial
    assert house.role.name == "Jefe de Servicio"
    assert house.sector_id == datos["sector_guardia"].id

    # Ascendemos a House a Administrador
    usuario_actualizado = assign_role(house.id, rol_admin.id)

    # Validaciones
    assert usuario_actualizado.role.name == "Administrador"
    assert usuario_actualizado.sector_id is None  # ¡Se desvinculó automáticamente!

def test_usuario_inexistente_lanza_excepcion(datos):
    """Intentar cambiar el rol a un ID de usuario que no existe."""
    rol_admin = datos["rol_admin"]
    
    with pytest.raises(UserNotFoundError) as excinfo:
        assign_role(999, rol_admin.id)
        
    assert "El usuario especificado no existe" in str(excinfo.value)

def test_rol_inexistente_lanza_excepcion(datos):
    """Intentar asignar un ID de rol que no existe en la base de datos."""
    ana = datos["empleada_ana"]
    
    with pytest.raises(RoleNotFoundError) as excinfo:
        assign_role(ana.id, 999)
        
    assert "El rol especificado no es válido" in str(excinfo.value)