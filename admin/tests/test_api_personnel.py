import pytest
import jwt
from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.sectors.models import Sector
from src.core.users.models import User
from src.core.personnel_types.models import PersonnelType
from src.core.menu_types.models import MenuType
from src.core.personnel.models import Personal

URL_PERSONNEL = "/api/personnel/"


@pytest.fixture
def app(monkeypatch):
    """App con base en memoria y SECRET_KEY para probar JWT."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="clave-secreta-de-prueba",
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
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def crear_usuario(email, rol, dni, sector_id=None):
    usuario = User(
        email=email,
        nombre="Usuario",
        apellido="Prueba",
        dni=dni,
        password="hash",
        activo=True,
        role_id=rol.id,
        sector_id=sector_id,
    )
    db.session.add(usuario)
    return usuario


@pytest.fixture
def datos(app):
    # Permisos de personal
    permisos = [
        Permission(name="personnel_index"),
        Permission(name="personnel_show"),
        Permission(name="personnel_new"),
        Permission(name="personnel_update"),
        Permission(name="personnel_destroy"),
    ]
    db.session.add_all(permisos)
    db.session.flush()

    # Sectores
    sec_guardia = Sector(nombre="Guardia", descripcion="Activo", activo=True)
    sec_quirofano = Sector(nombre="Quirófano", descripcion="Activo", activo=True)
    db.session.add_all([sec_guardia, sec_quirofano])
    db.session.flush()

    # Roles
    alim = Role(name="Servicio de Alimentación", permissions=permisos)
    jefe = Role(name="Jefe de Servicio", permissions=permisos)
    db.session.add_all([alim, jefe])
    db.session.flush()

    # Tipos de personal y menú
    tp_fijo = PersonnelType(nombre="Personal Fijo")
    tp_residente = PersonnelType(nombre="Residente")
    menu = MenuType(nombre="General")
    db.session.add_all([tp_fijo, tp_residente, menu])
    db.session.flush()

    # Usuarios
    user_alim = crear_usuario("alim@test.com", alim, "11111111")
    user_jefe = crear_usuario("jefe@test.com", jefe, "22222222", sector_id=sec_guardia.id)

    db.session.commit()

    return {
        "user_alim": user_alim,
        "user_jefe": user_jefe,
        "sec_guardia": sec_guardia,
        "sec_quirofano": sec_quirofano,
        "tp_fijo": tp_fijo,
        "tp_residente": tp_residente,
        "menu": menu,
    }


# ==========================================
# TESTS DE ACCESO (401)
# ==========================================

def test_personnel_sin_token_responde_401(client):
    assert client.get(URL_PERSONNEL).status_code == 401


# ==========================================
# TESTS LISTADO Y REGLAS DE JEFE DE SERVICIO
# ==========================================

def test_jefe_servicio_solo_ve_su_sector_y_residentes(app, client, datos):
    # Crear personal de su sector, de otro sector y un residente
    p_propio = Personal(dni="10101010", nombre="Ana", apellido="Propia", personnel_type_id=datos["tp_fijo"].id, sector_id=datos["sec_guardia"].id, menu_type_id=datos["menu"].id, activo=True)
    p_ajeno = Personal(dni="20202020", nombre="Beto", apellido="Ajeno", personnel_type_id=datos["tp_fijo"].id, sector_id=datos["sec_quirofano"].id, menu_type_id=datos["menu"].id, activo=True)
    p_resi = Personal(dni="30303030", nombre="Carla", apellido="Resi", personnel_type_id=datos["tp_residente"].id, sector_id=None, menu_type_id=datos["menu"].id, activo=True)

    db.session.add_all([p_propio, p_ajeno, p_resi])
    db.session.commit()

    headers = auth_headers(app, datos["user_jefe"])
    # Aunque el cliente pase sector_id de otro sector en query, se fuerza su sector
    res = client.get(f"{URL_PERSONNEL}?sector_id={datos['sec_quirofano'].id}", headers=headers)
    assert res.status_code == 200

    data = res.get_json()
    items = data.get("items", data) if isinstance(data, dict) else data
    dnis = [item["dni"] for item in items]

    assert "10101010" in dnis
    assert "30303030" in dnis
    assert "20202020" not in dnis


def test_jefe_servicio_detalle_personal_ajeno_responde_403(app, client, datos):
    p_ajeno = Personal(dni="40404040", nombre="Daniel", apellido="Ajeno", personnel_type_id=datos["tp_fijo"].id, sector_id=datos["sec_quirofano"].id, menu_type_id=datos["menu"].id, activo=True)
    db.session.add(p_ajeno)
    db.session.commit()

    headers = auth_headers(app, datos["user_jefe"])
    res = client.get(f"{URL_PERSONNEL}{p_ajeno.id}", headers=headers)
    assert res.status_code == 403


# ==========================================
# TESTS CREACIÓN Y RESTRICCIONES
# ==========================================

def test_crear_personal_exitoso_y_duplicado_409(app, client, datos):
    headers = auth_headers(app, datos["user_alim"])
    payload = {
        "dni": "50505050",
        "nombre": "Elena",
        "apellido": "Perez",
        "personnel_type_id": datos["tp_fijo"].id,
        "sector_id": datos["sec_guardia"].id,
        "menu_type_id": datos["menu"].id,
    }

    res = client.post(URL_PERSONNEL, json=payload, headers=headers)
    assert res.status_code in [200, 201]

    # Mismo DNI debe rechazar con 409
    res_dup = client.post(URL_PERSONNEL, json=payload, headers=headers)
    assert res_dup.status_code == 409


def test_jefe_servicio_no_puede_crear_residente(app, client, datos):
    headers = auth_headers(app, datos["user_jefe"])
    payload = {
        "dni": "60606060",
        "nombre": "Franco",
        "apellido": "Gomez",
        "personnel_type_id": datos["tp_residente"].id,
        "menu_type_id": datos["menu"].id,
    }

    res = client.post(URL_PERSONNEL, json=payload, headers=headers)
    assert res.status_code == 403


def test_eliminar_personal_inexistente_responde_404(app, client, datos):
    headers = auth_headers(app, datos["user_alim"])
    res = client.delete(f"{URL_PERSONNEL}99999", headers=headers)
    assert res.status_code == 404