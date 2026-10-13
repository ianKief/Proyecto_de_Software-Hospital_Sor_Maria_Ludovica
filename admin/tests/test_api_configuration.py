"""Tests de GET /api/configuration (usan una base SQLite en memoria).

La spec pide que este endpoint lo pueda usar "cualquier usuario autenticado":
sin sesión responde 401 y con cualquier usuario logueado (aunque no sea
Administrador ni tenga permisos) responde 200 con los ajustes.
"""
import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.users.models import User


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
def usuario_comedor(app):
    """Crea un usuario del Sector Comedor, con un rol sin ningún permiso."""
    rol = Role(name="Sector Comedor")
    db.session.add(rol)
    db.session.flush()

    usuario = User(
        email="comedor@test.com",
        nombre="Usuario",
        apellido="Comedor",
        dni="20000002",
        password="hash-de-prueba",
        activo=True,
        role_id=rol.id,
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


def test_sin_sesion_responde_401(app):
    """Sin sesión iniciada, el endpoint responde 401 en JSON."""
    respuesta = app.test_client().get("/api/configuration")

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "Debe iniciar sesión."}


def test_usuario_no_admin_con_sesion_responde_200(app, usuario_comedor):
    """Un usuario logueado que no es Administrador recibe los tres ajustes.

    La spec dice "Rol(es): cualquier usuario autenticado", así que no se pide
    ningún permiso (el rol del usuario no tiene ``config_show``).
    """
    client = app.test_client()
    with client.session_transaction() as session:
        session["user"] = usuario_comedor.email
        session["user_id"] = usuario_comedor.id
        session["role"] = "Sector Comedor"

    respuesta = client.get("/api/configuration")

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "elementos_por_pagina": 10,
        "mantenimiento_activo": False,
        "mensaje_mantenimiento": None,
    }
