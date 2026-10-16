import pytest
import jwt
from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.sectors.models import Sector
from src.core.users.models import User

URL_INDEX = "/api/sectors/"

@pytest.fixture
def app(monkeypatch):
    """App con base en memoria y SECRET_KEY para probar JWT."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    
    app = create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="clave-secreta-de-prueba" # Necesaria para firmar el token
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def auth_headers(app, user):
    """Genera el header de autorización Bearer con un token JWT válido."""
    token = jwt.encode(
        {"sub": str(user.id)}, 
        app.config["SECRET_KEY"], 
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}

def crear_usuario(email, rol, dni):
    """Crea un usuario activo asociado a un rol y un DNI único."""
    usuario = User(
        email=email,
        nombre="Usuario",
        apellido="Prueba",
        dni=dni,
        password="hash",
        activo=True,
        role_id=rol.id,
    )
    db.session.add(usuario)
    return usuario

@pytest.fixture
def datos(app):
    """Prepara roles, usuarios y sectores para los tests."""
    perm_index = Permission(name="sector_index")
    perm_show = Permission(name="sector_show")
    
    alimentacion = Role(name="Servicio de Alimentación", permissions=[perm_index, perm_show])
    comedor = Role(name="Sector Comedor", permissions=[perm_index, perm_show])
    jefe = Role(name="Jefe de Servicio", permissions=[])
    
    db.session.add_all([perm_index, perm_show, alimentacion, comedor, jefe])
    db.session.flush()

    user_alim = crear_usuario("alim@test.com", alimentacion, "11111111")
    user_comedor = crear_usuario("comedor@test.com", comedor, "22222222")
    user_jefe = crear_usuario("jefe@test.com", jefe, "33333333")
    
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
    """Acceso denegado si no hay header Authorization."""
    assert client.get(URL_INDEX).status_code == 401

def test_jefe_servicio_sin_permiso_responde_403(app, client, datos):
    """Un Jefe no tiene sector_index, responde 403."""
    headers = auth_headers(app, datos["user_jefe"])
    assert client.get(URL_INDEX, headers=headers).status_code == 403
    
def test_jefe_servicio_sin_permiso_show_responde_403(app, client, datos):
    headers = auth_headers(app, datos["user_jefe"])
    url_show = f"{URL_INDEX}{datos['sector_activo'].id}"
    assert client.get(url_show, headers=headers).status_code == 403


# ==========================================
# TESTS ENDPOINT: GET /api/sectors/
# ==========================================

def test_list_sectors_devuelve_solo_activos_por_defecto(app, client, datos):
    headers = auth_headers(app, datos["user_alim"])
    res = client.get(URL_INDEX, headers=headers)
    
    assert res.status_code == 200
    json_data = res.get_json()
    assert len(json_data) == 1
    assert json_data[0]["nombre"] == "Guardia"

def test_list_sectors_devuelve_todos(app, client, datos):
    headers = auth_headers(app, datos["user_comedor"])
    res = client.get(URL_INDEX, query_string={"estado": "todos"}, headers=headers)
    
    assert res.status_code == 200
    assert len(res.get_json()) == 2


# ==========================================
# TESTS ENDPOINT: GET /api/sectors/<id>
# ==========================================

def test_get_sector_existente(app, client, datos):
    headers = auth_headers(app, datos["user_alim"])
    sector_id = datos["sector_inactivo"].id
    
    res = client.get(f"{URL_INDEX}{sector_id}", headers=headers)
    
    assert res.status_code == 200
    assert res.get_json()["nombre"] == "Archivo"

def test_get_sector_inexistente_responde_404(app, client, datos):
    headers = auth_headers(app, datos["user_alim"])
    res = client.get(f"{URL_INDEX}9999", headers=headers)
    
    assert res.status_code == 404