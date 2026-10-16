import pytest
import jwt
from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.sectors.models import Sector
from src.core.users.models import User
from src.core.quotas.models import Cupo
from src.core.food_types.models import FoodType

URL_QUOTAS = "/api/quotas/"


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
    # Permisos de cupos
    permisos = [
        Permission(name="quota_index"),
        Permission(name="quota_show"),
        Permission(name="quota_new"),
        Permission(name="quota_update"),
    ]
    db.session.add_all(permisos)
    db.session.flush()

    # Sectores
    sec_guardia = Sector(nombre="Guardia", descripcion="Activo", activo=True)
    sec_pediatria = Sector(nombre="Pediatría", descripcion="Activo", activo=True)
    sec_inactivo = Sector(nombre="Archivo", descripcion="Inactivo", activo=False)
    db.session.add_all([sec_guardia, sec_pediatria, sec_inactivo])
    db.session.flush()

    # Tipos de comida
    ft_almuerzo = FoodType(nombre="Almuerzo")
    ft_cena = FoodType(nombre="Cena")
    db.session.add_all([ft_almuerzo, ft_cena])
    db.session.flush()

    # Roles
    alim = Role(name="Servicio de Alimentación", permissions=permisos)
    jefe = Role(name="Jefe de Servicio", permissions=permisos)
    db.session.add_all([alim, jefe])
    db.session.flush()

    # Usuarios
    user_alim = crear_usuario("alim@test.com", alim, "11111111")
    user_jefe = crear_usuario("jefe@test.com", jefe, "22222222", sector_id=sec_guardia.id)

    db.session.commit()

    return {
        "user_alim": user_alim,
        "user_jefe": user_jefe,
        "sec_guardia": sec_guardia,
        "sec_pediatria": sec_pediatria,
        "sec_inactivo": sec_inactivo,
        "ft_almuerzo": ft_almuerzo,
        "ft_cena": ft_cena,
    }


# ==========================================
# TESTS DE ACCESO (401)
# ==========================================

def test_quotas_sin_token_responde_401(client):
    assert client.get(URL_QUOTAS).status_code == 401


# ==========================================
# TESTS LISTADO Y REGLAS DE JEFE DE SERVICIO
# ==========================================

def test_jefe_servicio_solo_puede_ver_cupos_de_su_sector(app, client, datos):
    headers = auth_headers(app, datos["user_jefe"])

    # Pedir otro sector explícitamente debe responder 403
    res_ajeno = client.get(f"{URL_QUOTAS}?sector_id={datos['sec_pediatria'].id}", headers=headers)
    assert res_ajeno.status_code == 403

    # Consultar sin parámetros responde 200 con su sector
    res_propio = client.get(URL_QUOTAS, headers=headers)
    assert res_propio.status_code == 200


def test_jefe_servicio_no_puede_crear_cupos(app, client, datos):
    headers = auth_headers(app, datos["user_jefe"])
    payload = {
        "sector_id": datos["sec_guardia"].id,
        "food_type_id": datos["ft_almuerzo"].id,
        "tipo_comida_id": datos["ft_almuerzo"].id,
        "cantidad": 10,
    }

    res = client.post(URL_QUOTAS, json=payload, headers=headers)
    assert res.status_code == 403


# ==========================================
# TESTS CREACIÓN Y REGLAS DE NEGOCIO
# ==========================================

def test_crear_cupo_exitoso_servicio_alimentacion(app, client, datos):
    headers = auth_headers(app, datos["user_alim"])
    payload = {
        "sector_id": datos["sec_guardia"].id,
        "food_type_id": datos["ft_cena"].id,
        "tipo_comida_id": datos["ft_cena"].id,
        "cantidad": 25,
    }

    res = client.post(URL_QUOTAS, json=payload, headers=headers)
    assert res.status_code in [200, 201]
    data = res.get_json()
    assert data["cantidad"] == 25


def test_no_se_puede_crear_cupo_para_sector_inactivo(app, client, datos):
    headers = auth_headers(app, datos["user_alim"])
    payload = {
        "sector_id": datos["sec_inactivo"].id,
        "food_type_id": datos["ft_almuerzo"].id,
        "tipo_comida_id": datos["ft_almuerzo"].id,
        "cantidad": 15,
    }

    res = client.post(URL_QUOTAS, json=payload, headers=headers)
    assert res.status_code == 400


def test_modificar_cupo_inexistente_responde_404(app, client, datos):
    headers = auth_headers(app, datos["user_alim"])
    res = client.put(f"{URL_QUOTAS}99999", json={"cantidad": 50}, headers=headers)
    assert res.status_code in [400, 404]