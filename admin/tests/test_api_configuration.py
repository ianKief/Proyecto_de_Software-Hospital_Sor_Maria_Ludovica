"""Tests de GET /api/configuration (usan una base SQLite en memoria).

La spec pide que este endpoint lo pueda usar "cualquier usuario autenticado":
sin token responde 401 y con el token de cualquier usuario (aunque no sea
Administrador ni tenga permisos) responde 200 con los ajustes.

También se prueba el modo mantenimiento en la API: el Administrador
(``config_update``) pasa, otro rol recibe 503 y sin token sigue siendo 401.
"""
import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.users.models import User
from tests.helpers_token import cliente_con_token, headers_con_token

URL = "/api/configuration"
MENSAJE = "Volvemos en una hora"


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


def crear_usuario(email, dni, rol):
    """Crea un usuario activo con el rol dado (sin guardar todavía)."""
    return User(
        email=email,
        nombre="Usuario",
        apellido="Prueba",
        dni=dni,
        password="hash-de-prueba",
        activo=True,
        role_id=rol.id,
    )


@pytest.fixture
def usuario_comedor(app):
    """Crea un usuario del Sector Comedor, con un rol sin ningún permiso."""
    rol = Role(name="Sector Comedor")
    db.session.add(rol)
    db.session.flush()

    usuario = crear_usuario("comedor@test.com", "20000002", rol)
    db.session.add(usuario)
    db.session.commit()
    return usuario


@pytest.fixture
def usuario_admin(app):
    """Crea un Administrador, con el permiso ``config_update``."""
    rol = Role(name="Administrador", permissions=[Permission(name="config_update")])
    db.session.add(rol)
    db.session.flush()

    usuario = crear_usuario("admin@test.com", "20000001", rol)
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


# Acceso

def test_sin_token_responde_401(app):
    """Sin token, el endpoint responde 401 en JSON."""
    respuesta = app.test_client().get(URL)

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "Token faltante o inválido"}


def test_token_expirado_responde_401(app, usuario_comedor):
    """Con un token vencido responde 401 aunque el usuario exista."""
    headers = headers_con_token(app, usuario_comedor, horas=-1)

    respuesta = app.test_client().get(URL, headers=headers)

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "Token expirado"}


def test_usuario_no_admin_con_token_responde_200(app, usuario_comedor):
    """Un usuario con token que no es Administrador recibe los tres ajustes.

    La spec dice "Rol(es): cualquier usuario autenticado", así que no se pide
    ningún permiso (el rol del usuario no tiene ``config_show``).
    """
    respuesta = cliente_con_token(app, usuario_comedor).get(URL)

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "elementos_por_pagina": 10,
        "mantenimiento_activo": False,
        "mensaje_mantenimiento": None,
    }


# Modo mantenimiento

def test_mantenimiento_admin_pasa(app, usuario_admin, en_mantenimiento):
    """El Administrador sigue usando la API para poder desactivarlo."""
    respuesta = cliente_con_token(app, usuario_admin).get(URL)

    assert respuesta.status_code == 200
    assert respuesta.get_json()["mantenimiento_activo"] is True


def test_mantenimiento_otro_rol_responde_503(app, usuario_comedor, en_mantenimiento):
    """Un rol sin ``config_update`` recibe 503 con el mensaje configurado."""
    respuesta = cliente_con_token(app, usuario_comedor).get(URL)

    assert respuesta.status_code == 503
    assert respuesta.get_json() == {"error": MENSAJE}


def test_mantenimiento_sin_token_responde_401(app, en_mantenimiento):
    """Sin token gana el 401 sobre el 503 (la spec lo pide primero)."""
    respuesta = app.test_client().get(URL)

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "Token faltante o inválido"}
