"""Tests del formulario de Ajustes del sistema (usan una base SQLite en memoria).

Se simula la sesión de un Administrador con ``session_transaction()``,
guardando lo mismo que guarda el login: el email en ``user`` y el id en ``user_id``.
"""
from datetime import time

import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.users.models import User

URL = "/configuration/"


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
def cliente_admin(app):
    """Cliente con la sesión iniciada por un Administrador (``config_show`` y ``config_update``)."""
    rol = Role(
        name="Administrador",
        permissions=[Permission(name="config_show"), Permission(name="config_update")],
    )
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

    cliente = app.test_client()
    with cliente.session_transaction() as sesion:
        sesion["user"] = usuario.email
        sesion["user_id"] = usuario.id
    return cliente


def formulario_valido():
    """Devuelve los campos del formulario de Ajustes con valores válidos."""
    return {
        "elementos_por_pagina": "10",
        "mensaje_mantenimiento": "",
        "desayuno_inicio": "06:00",
        "desayuno_fin": "10:00",
        "almuerzo_inicio": "12:00",
        "almuerzo_fin": "14:00",
        "merienda_inicio": "16:00",
        "merienda_fin": "18:30",
        "cena_inicio": "20:00",
        "cena_fin": "23:00",
        "horario_corte": "19:00",
    }


def test_guardar_horarios_validos(cliente_admin):
    """Con horarios válidos guarda las horas y redirige a la pantalla de Ajustes."""
    respuesta = cliente_admin.post(URL, data=formulario_valido())

    assert respuesta.status_code == 302
    configuracion = db.session.get(Configuration, ID_CONFIGURACION)
    assert configuracion.almuerzo_inicio == time(12, 0)
    assert configuracion.almuerzo_fin == time(14, 0)
    assert configuracion.horario_corte == time(19, 0)


def test_horarios_superpuestos_muestra_error(cliente_admin):
    """Si una comida se superpone con la siguiente, muestra el error y no guarda nada."""
    datos = formulario_valido()
    datos["almuerzo_fin"] = "16:30"

    respuesta = cliente_admin.post(URL, data=datos)

    assert respuesta.status_code == 422
    html = respuesta.get_data(as_text=True)
    assert "El almuerzo no puede terminar después de que empiece la merienda" in html
    configuracion = db.session.get(Configuration, ID_CONFIGURACION)
    assert configuracion.almuerzo_fin == time(15, 0)


def test_superposicion_marca_solo_el_campo_modificado(cliente_admin):
    """Si solo cambió el fin del almuerzo, el error se muestra solo en ese campo.

    El inicio de la merienda del formulario (16:00) es igual al guardado,
    así que no se marca aunque el validador lo devuelva junto con el otro.
    """
    datos = formulario_valido()
    datos["almuerzo_fin"] = "16:30"

    respuesta = cliente_admin.post(URL, data=datos)

    assert respuesta.status_code == 422
    html = respuesta.get_data(as_text=True)
    assert 'id="almuerzo_fin-error"' in html
    assert 'id="merienda_inicio-error"' not in html
