"""Tests del modo mantenimiento en la API (usan una base SQLite en memoria).

Mientras el mantenimiento está activo, toda la API responde 503 con el
mensaje, con o sin token y también el login. La única excepción es
``GET /api/configuration``, que el portal usa para mostrar la pantalla de
mantenimiento y para saber si hay conexión. Los OPTIONS tampoco se cortan.
"""
import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.users.models import User
from tests.helpers_token import cliente_con_token

MENSAJE = "Volvemos en una hora"
URL_LOGIN = "/api/auth/login"
URL_ME = "/api/auth/me"
URL_CONFIGURACION = "/api/configuration"


@pytest.fixture
def app(monkeypatch):
    """App con base en memoria, todas las tablas y la fila de configuración."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        db.session.add(Configuration(
            id=ID_CONFIGURACION,
            elementos_por_pagina=10,
            mantenimiento_activo=False,
        ))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def usuario_admin(app):
    """Crea un Administrador, con el permiso ``config_update``."""
    rol = Role(name="Administrador", permissions=[Permission(name="config_update")])
    db.session.add(rol)
    db.session.flush()

    usuario = User(
        email="admin@test.com",
        nombre="Usuario",
        apellido="Prueba",
        dni="20000001",
        password="hash-de-prueba",
        activo=True,
        role_id=rol.id,
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


@pytest.fixture
def en_mantenimiento(app):
    """Activa el modo mantenimiento con un mensaje."""
    configuracion = db.session.get(Configuration, ID_CONFIGURACION)
    configuracion.mantenimiento_activo = True
    configuracion.mensaje_mantenimiento = MENSAJE
    db.session.commit()


def datos_de_login():
    """Devuelve un login con credenciales que no existen."""
    return {"email": "nadie@test.com", "password": "incorrecta"}


# Mantenimiento activo

def test_login_responde_503(app, en_mantenimiento):
    """El login de la API también se corta: no se pueden pedir tokens nuevos."""
    respuesta = app.test_client().post(URL_LOGIN, json=datos_de_login())

    assert respuesta.status_code == 503
    assert respuesta.get_json() == {"error": MENSAJE}


def test_endpoint_con_token_responde_503(app, usuario_admin, en_mantenimiento):
    """Con token también responde 503, aunque sea el Administrador."""
    respuesta = cliente_con_token(app, usuario_admin).get(URL_ME)

    assert respuesta.status_code == 503
    assert respuesta.get_json() == {"error": MENSAJE}


def test_endpoint_sin_token_responde_503(app, en_mantenimiento):
    """Sin token responde 503 y no 401: el mantenimiento va primero."""
    respuesta = app.test_client().get(URL_ME)

    assert respuesta.status_code == 503
    assert respuesta.get_json() == {"error": MENSAJE}


def test_options_no_responde_503(app, en_mantenimiento):
    """Un OPTIONS (el que manda el navegador antes de un pedido con CORS) no se corta."""
    respuesta = app.test_client().options(URL_ME)

    assert respuesta.status_code != 503


def test_configuracion_responde_200_en_mantenimiento(app, en_mantenimiento):
    """GET /api/configuration sigue funcionando y avisa que hay mantenimiento."""
    respuesta = app.test_client().get(URL_CONFIGURACION)

    assert respuesta.status_code == 200
    assert respuesta.get_json()["mantenimiento_activo"] is True
    assert respuesta.get_json()["mensaje_mantenimiento"] == MENSAJE


# Mantenimiento apagado: todo funciona normal

def test_sin_mantenimiento_endpoint_con_token_responde_200(app, usuario_admin):
    """Con el mantenimiento apagado, un endpoint con token responde normal."""
    respuesta = cliente_con_token(app, usuario_admin).get(URL_ME)

    assert respuesta.status_code == 200
    assert respuesta.get_json()["email"] == "admin@test.com"


def test_sin_mantenimiento_endpoint_sin_token_responde_401(app):
    """Con el mantenimiento apagado, sin token vuelve el 401 de siempre."""
    respuesta = app.test_client().get(URL_ME)

    assert respuesta.status_code == 401


def test_sin_mantenimiento_login_invalido_responde_401(app):
    """Con el mantenimiento apagado, el login funciona y rechaza credenciales inválidas."""
    respuesta = app.test_client().post(URL_LOGIN, json=datos_de_login())

    assert respuesta.status_code == 401
