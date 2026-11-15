"""Tests de los endpoints de autenticación y perfil de la API (/api/auth/*)."""
import bcrypt
import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role
from src.core.sectors.models import Sector
from src.core.users.models import User
from src.core.configuration.models import Configuration, ID_CONFIGURACION
from src.web.helpers import auth_validaciones
from tests.helpers_token import cliente_con_token, headers_con_token


def _hash_password(texto):
    return bcrypt.hashpw(texto.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app(env="testing")
    app.config.update(
        TESTING=True,
        GOOGLE_CLIENT_ID="test-google-client-id.apps.googleusercontent.com",
    )

    with app.app_context():
        db.create_all()
        db.session.add(Configuration(
            id=ID_CONFIGURACION,
            elementos_por_pagina=25,
            mantenimiento_activo=False,
        ))

        rol_admin = Role(name="Administrador")
        rol_jefe = Role(name="Jefe de Servicio")
        rol_alim = Role(name="Servicio de Alimentación")
        rol_comedor = Role(name="Sector Comedor")

        sector_pediatria = Sector(
            nombre="Pediatría",
            descripcion="Sector de Pediatría",
            activo=True,
        )

        db.session.add_all([rol_admin, rol_jefe, rol_alim, rol_comedor, sector_pediatria])
        db.session.flush()

        admin = User(
            email="admin@hospital.com",
            nombre="Carlos",
            apellido="Admin",
            dni="11223344",
            password=_hash_password("admin123"),
            activo=True,
            role_id=rol_admin.id,
        )
        jefe = User(
            email="jefe@hospital.com",
            nombre="Laura",
            apellido="Gómez",
            dni="22334455",
            password=_hash_password("jefe123"),
            activo=True,
            role_id=rol_jefe.id,
            sector_id=sector_pediatria.id,
        )
        comedor = User(
            email="comedor@hospital.com",
            nombre="Martín",
            apellido="Pérez",
            dni="33445566",
            password=_hash_password("comedor123"),
            activo=True,
            role_id=rol_comedor.id,
        )
        bloqueado = User(
            email="bloqueado@hospital.com",
            nombre="Diego",
            apellido="Inactivo",
            dni="44556677",
            password=_hash_password("bloqueado123"),
            activo=False,
            role_id=rol_alim.id,
        )

        db.session.add_all([admin, jefe, comedor, bloqueado])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def test_api_login_exitoso_rol_operativo(app):
    resp = app.test_client().post("/api/auth/login", json={
        "email": "jefe@hospital.com",
        "password": "jefe123",
    })

    assert resp.status_code == 200
    body = resp.get_json()
    assert "token" in body and isinstance(body["token"], str)
    assert body["user"]["email"] == "jefe@hospital.com"
    assert body["user"]["rol"] == "Jefe de Servicio"
    assert body["user"]["sector"] == "Pediatría"
    assert body["user"]["sector_id"] is not None


def test_api_login_rechaza_administrador_con_403(app):
    resp = app.test_client().post("/api/auth/login", json={
        "email": "admin@hospital.com",
        "password": "admin123",
    })

    assert resp.status_code == 403
    assert "Administrador" in resp.get_json()["error"]


def test_api_login_rechaza_usuario_bloqueado_con_403(app):
    resp = app.test_client().post("/api/auth/login", json={
        "email": "bloqueado@hospital.com",
        "password": "bloqueado123",
    })

    assert resp.status_code == 403
    assert "bloqueada o inactiva" in resp.get_json()["error"]


def test_api_login_rechaza_credenciales_invalidas_con_401(app):
    resp = app.test_client().post("/api/auth/login", json={
        "email": "jefe@hospital.com",
        "password": "clave_incorrecta",
    })

    assert resp.status_code == 401
    assert "Credenciales inválidas" in resp.get_json()["error"]


def test_api_login_datos_faltantes_o_invalidos_responde_400(app):
    client = app.test_client()

    assert client.post("/api/auth/login", json={}).status_code == 400
    assert client.post("/api/auth/login", json={"email": "no-es-email", "password": "123"}).status_code == 400


def test_api_google_login_exitoso(app, monkeypatch):
    def fake_verify(token_str, req, audience=None):
        assert token_str == "token-valido-google"
        return {
            "iss": "https://accounts.google.com",
            "aud": app.config["GOOGLE_CLIENT_ID"],
            "email": "jefe@hospital.com",
            "email_verified": True,
        }

    monkeypatch.setattr(auth_validaciones.google_id_token, "verify_oauth2_token", fake_verify)

    resp = app.test_client().post("/api/auth/google", json={"id_token": "token-valido-google"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "token" in body and isinstance(body["token"], str)
    assert body["user"]["email"] == "jefe@hospital.com"
    assert body["user"]["rol"] == "Jefe de Servicio"


def test_api_google_login_sin_token_responde_400(app):
    resp = app.test_client().post("/api/auth/google", json={})
    assert resp.status_code == 400
    assert "id_token" in resp.get_json()["error"]


def test_api_google_login_token_invalido_o_vencido_responde_401(app, monkeypatch):
    def fake_verify_error(token_str, req, audience=None):
        raise ValueError("Token expired")

    monkeypatch.setattr(auth_validaciones.google_id_token, "verify_oauth2_token", fake_verify_error)

    resp = app.test_client().post("/api/auth/google", json={"id_token": "token-vencido"})
    assert resp.status_code == 401
    assert "inválido o ha expirado" in resp.get_json()["error"]


def test_api_google_login_email_no_registrado_responde_403(app, monkeypatch):
    def fake_verify(token_str, req, audience=None):
        return {
            "iss": "accounts.google.com",
            "aud": app.config["GOOGLE_CLIENT_ID"],
            "email": "desconocido@gmail.com",
            "email_verified": True,
        }

    monkeypatch.setattr(auth_validaciones.google_id_token, "verify_oauth2_token", fake_verify)

    resp = app.test_client().post("/api/auth/google", json={"id_token": "token-desconocido"})
    assert resp.status_code == 403
    assert "solicitar el alta al Administrador" in resp.get_json()["error"]


def test_api_google_login_rechaza_admin_y_bloqueado_con_403(app, monkeypatch):
    email_actual = {"valor": "admin@hospital.com"}

    def fake_verify(token_str, req, audience=None):
        return {
            "iss": "https://accounts.google.com",
            "aud": app.config["GOOGLE_CLIENT_ID"],
            "email": email_actual["valor"],
            "email_verified": True,
        }

    monkeypatch.setattr(auth_validaciones.google_id_token, "verify_oauth2_token", fake_verify)

    resp_admin = app.test_client().post("/api/auth/google", json={"id_token": "token-admin"})
    assert resp_admin.status_code == 403
    assert "Administrador" in resp_admin.get_json()["error"]

    email_actual["valor"] = "bloqueado@hospital.com"
    resp_bloq = app.test_client().post("/api/auth/google", json={"id_token": "token-bloq"})
    assert resp_bloq.status_code == 403
    assert "bloqueada o inactiva" in resp_bloq.get_json()["error"]


def test_api_me_devuelve_datos_usuario_y_valida_token(app):
    jefe = User.query.filter_by(email="jefe@hospital.com").first()

    resp_ok = cliente_con_token(app, jefe).get("/api/auth/me")
    assert resp_ok.status_code == 200
    datos = resp_ok.get_json()
    assert datos["nombre"] == "Laura"
    assert datos["dni"] == "22334455"
    assert datos["rol"] == "Jefe de Servicio"
    assert datos["sector"] == "Pediatría"
    assert datos["sector_id"] == jefe.sector_id

    # Sin token o con token expirado responde 401
    assert app.test_client().get("/api/auth/me").status_code == 401
    headers_vencido = headers_con_token(app, jefe, horas=-1)
    assert app.test_client().get("/api/auth/me", headers=headers_vencido).status_code == 401


def test_api_update_me_actualiza_perfil_y_valida_unicidad(app):
    jefe = User.query.filter_by(email="jefe@hospital.com").first()
    admin = User.query.filter_by(email="admin@hospital.com").first()

    # El Administrador no usa PUT /api/auth/me del portal
    resp_admin = cliente_con_token(app, admin).put("/api/auth/me", json={
        "nombre": "Carlos",
        "apellido": "Admin",
        "email": "admin@hospital.com",
        "dni": "11223344",
    })
    assert resp_admin.status_code == 403

    # Conflicto si intenta usar el email de otro usuario
    client_jefe = cliente_con_token(app, jefe)
    resp_duplicado = client_jefe.put("/api/auth/me", json={
        "nombre": "Laura",
        "apellido": "Gómez",
        "email": "comedor@hospital.com",
        "dni": "22334455",
    })
    assert resp_duplicado.status_code == 409
    assert "email" in resp_duplicado.get_json()["fields"]

    # Actualización válida de datos y contraseña
    resp_ok = client_jefe.put("/api/auth/me", json={
        "nombre": "Laura María",
        "apellido": "Gómez",
        "email": "jefe@hospital.com",
        "dni": "22334455",
        "password": "nueva_clave_jefe",
        "password_confirm": "nueva_clave_jefe",
    })
    assert resp_ok.status_code == 200
    assert resp_ok.get_json()["user"]["nombre"] == "Laura María"

    db.session.refresh(jefe)
    assert bcrypt.checkpw(b"nueva_clave_jefe", jefe.password.encode("utf-8"))


def test_api_logout_y_cors_headers(app):
    jefe = User.query.filter_by(email="jefe@hospital.com").first()

    resp_options = app.test_client().options(
        "/api/auth/login",
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp_options.status_code == 204
    assert resp_options.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert "Authorization" in resp_options.headers.get("Access-Control-Allow-Headers", "")

    resp_logout = cliente_con_token(app, jefe).post("/api/auth/logout")
    assert resp_logout.status_code == 200
    assert app.test_client().post("/api/auth/logout").status_code == 401
