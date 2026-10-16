import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.sectors.models import Sector
from src.core.users.models import User

URL_INDEX = "/api/sectors/"


@pytest.fixture
def app(monkeypatch):
    """App con base en memoria para pruebas."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def login_client(client, usuario):
    """Fuerza el inicio de sesión inyectando los datos en la sesión de Flask."""
    with client.session_transaction() as sess:
        sess["user"] = usuario.email
        sess["user_id"] = usuario.id
    return client

def crear_usuario(email, rol, dni):
    """Crea un usuario activo asociado a un rol y un DNI único."""
    usuario = User(
        email=email,
        nombre="Usuario",
        apellido="Prueba",
        dni=dni,  # <- Ahora usa el DNI que le pasamos
        password="hash",
        activo=True,
        role_id=rol.id,
    )
    db.session.add(usuario)
    return usuario


@pytest.fixture
def datos(app):
    """Prepara permisos, roles, usuarios y sectores para los tests."""
    # 1. Permisos
    perm_index = Permission(name="sector_index")
    perm_show = Permission(name="sector_show")
    
    # 2. Roles
    alimentacion = Role(
        name="Servicio de Alimentación", 
        permissions=[perm_index, perm_show]
    )
    comedor = Role(
        name="Sector Comedor", 
        permissions=[perm_index, perm_show]
    )
    jefe = Role(
        name="Jefe de Servicio", 
        permissions=[]  # No tiene permisos de API general de sectores
    )
    db.session.add_all([perm_index, perm_show, alimentacion, comedor, jefe])
    db.session.flush()

    # 3. Usuarios (¡Ahora con DNIs únicos!)
    user_alim = crear_usuario("alim@test.com", alimentacion, "11111111")
    user_comedor = crear_usuario("comedor@test.com", comedor, "22222222")
    user_jefe = crear_usuario("jefe@test.com", jefe, "33333333")
    
    # 4. Sectores
    sector_activo = Sector(nombre="Guardia", descripcion="Activo", activo=True)
    sector_inactivo = Sector(nombre="Archivo", descripcion="Inactivo", activo=False)
    db.session.add_all([sector_activo, sector_inactivo])
    db.session.commit()

    return {
        "user_alim": user_alim,
        "user_comedor": user_comedor,
        "user_jefe": user_jefe,
        "sector_activo": sector_activo,
        "sector_inactivo": sector_inactivo,
    }


# ==========================================
# TESTS DE ACCESO Y PERMISOS (401 y 403)
# ==========================================

def test_sin_sesion_responde_401(client):
    """Acceso denegado si no hay sesión iniciada."""
    assert client.get(URL_INDEX).status_code == 401

def test_jefe_servicio_sin_permiso_responde_403(client, datos):
    """Un Jefe de Servicio no tiene sector_index, responde 403."""
    client = login_client(client, datos["user_jefe"])
    assert client.get(URL_INDEX).status_code == 403
    
def test_jefe_servicio_sin_permiso_show_responde_403(client, datos):
    """Un Jefe de Servicio no tiene sector_show, responde 403."""
    client = login_client(client, datos["user_jefe"])
    url_show = f"{URL_INDEX}{datos['sector_activo'].id}"
    assert client.get(url_show).status_code == 403


# ==========================================
# TESTS ENDPOINT: GET /api/sectors/
# ==========================================

def test_list_sectors_devuelve_solo_activos_por_defecto(client, datos):
    """Si no se pasa estado, por defecto filtra activos."""
    client = login_client(client, datos["user_alim"])
    res = client.get(URL_INDEX)
    
    assert res.status_code == 200
    json_data = res.get_json()
    assert len(json_data) == 1
    assert json_data[0]["nombre"] == "Guardia"
    assert json_data[0]["estado"] == "activo"

def test_list_sectors_devuelve_todos(client, datos):
    """Si se pasa estado=todos, devuelve activos e inactivos."""
    client = login_client(client, datos["user_comedor"])
    res = client.get(URL_INDEX, query_string={"estado": "todos"})
    
    assert res.status_code == 200
    json_data = res.get_json()
    assert len(json_data) == 2
    nombres = [s["nombre"] for s in json_data]
    assert "Guardia" in nombres
    assert "Archivo" in nombres


# ==========================================
# TESTS ENDPOINT: GET /api/sectors/<id>
# ==========================================

def test_get_sector_existente(client, datos):
    """Devuelve 200 y el JSON del sector, incluso si está inactivo."""
    client = login_client(client, datos["user_alim"])
    sector_inactivo_id = datos["sector_inactivo"].id
    
    res = client.get(f"{URL_INDEX}{sector_inactivo_id}")
    
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["id"] == sector_inactivo_id
    assert json_data["nombre"] == "Archivo"
    assert json_data["estado"] == "inactivo"

def test_get_sector_inexistente_responde_404(client, datos):
    """Devuelve 404 si el ID no existe."""
    client = login_client(client, datos["user_alim"])
    
    res = client.get(f"{URL_INDEX}9999")
    
    assert res.status_code == 404
    assert "no existe" in res.get_json()["error"]