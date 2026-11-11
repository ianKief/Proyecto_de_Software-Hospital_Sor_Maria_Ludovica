"""Tests de GET /api/configuration (usan una base SQLite en memoria).

En la etapa 2 el endpoint es público: el portal lo consulta antes del login
para saber si hay mantenimiento y si hay conexión. Responde 200 con o sin
token, con los parámetros generales, el horario de corte y los horarios
de cada comida.

También se prueba el modo mantenimiento en la API sobre este endpoint.
"""
import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.users.models import User
from tests.helpers_token import cliente_con_token

URL = "/api/configuration"
MENSAJE = "Volvemos en una hora"

# Lo que devuelve el endpoint con la fila de la fixture: los horarios no se
# cargan ahí, así que valen los iniciales (default= del modelo).
CONFIGURACION_ESPERADA = {
    "elementos_por_pagina": 10,
    "mantenimiento_activo": False,
    "mensaje_mantenimiento": None,
    "horario_corte": "20:00",
    "comidas": {
        "desayuno": {"inicio": "06:00", "fin": "10:00"},
        "almuerzo": {"inicio": "11:30", "fin": "15:00"},
        "merienda": {"inicio": "16:00", "fin": "18:30"},
        "cena": {"inicio": "20:00", "fin": "23:00"},
    },
}


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

def test_sin_token_responde_200(app):
    """Sin token responde 200 con todos los ajustes (el endpoint es público)."""
    respuesta = app.test_client().get(URL)

    assert respuesta.status_code == 200
    assert respuesta.get_json() == CONFIGURACION_ESPERADA


def test_usuario_no_admin_con_token_responde_200(app, usuario_comedor):
    """Con el token de un usuario sin permisos también responde 200 con los ajustes."""
    respuesta = cliente_con_token(app, usuario_comedor).get(URL)

    assert respuesta.status_code == 200
    assert respuesta.get_json() == CONFIGURACION_ESPERADA


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


def test_mantenimiento_sin_token_responde_200(app, en_mantenimiento):
    """Sin token responde 200 y avisa que hay mantenimiento, con el mensaje."""
    respuesta = app.test_client().get(URL)

    assert respuesta.status_code == 200
    assert respuesta.get_json()["mantenimiento_activo"] is True
    assert respuesta.get_json()["mensaje_mantenimiento"] == MENSAJE
