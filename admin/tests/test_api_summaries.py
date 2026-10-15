from datetime import date

import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Autorizacion, Carga, Pedido, SolicitudPedido
from src.core.personnel.models import Personal
from src.core.personnel_types.models import PersonnelType
from src.core.sectors.models import Sector
from src.core.users.models import User


URL_REQUESTS = "/api/summaries/requests"
URL_AUTHORIZATIONS = "/api/summaries/authorizations"
FECHA_PEDIDO = date(2026, 10, 13)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()

        db.session.add(Configuration(
            id=ID_CONFIGURACION,
            elementos_por_pagina=25,
            mantenimiento_activo=False,
        ))
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def crear_cliente_con_sesion(app, usuario):
    client = app.test_client()

    with client.session_transaction() as session:
        session["user"] = usuario.email
        session["user_id"] = usuario.id
        session["role"] = usuario.role.name

    return client


@pytest.fixture
def datos(app):
    permiso_requests = Permission(name="summary_requests")
    permiso_authorizations = Permission(name="summary_authorizations")

    rol_alimentacion = Role(
        name="Servicio de Alimentación",
        permissions=[permiso_requests, permiso_authorizations],
    )
    rol_sin_permisos = Role(name="Sin permisos")

    sector = Sector(
        nombre="Sector de prueba",
        descripcion="Sector para probar resúmenes",
        activo=True,
    )

    tipo_personal = PersonnelType(nombre="Personal Fijo")
    menu_general = MenuType(nombre="General")
    menu_celiaco = MenuType(nombre="Celíaco")
    comida = FoodType(nombre="Almuerzo")

    db.session.add_all([
        rol_alimentacion,
        rol_sin_permisos,
        sector,
        tipo_personal,
        menu_general,
        menu_celiaco,
        comida,
    ])
    db.session.flush()

    usuario = User(
        email="alimentacion@test.com",
        nombre="Usuario",
        apellido="Alimentación",
        dni="20000001",
        password="hash-de-prueba",
        activo=True,
        role_id=rol_alimentacion.id,
    )

    usuario_sin_permisos = User(
        email="sinpermisos@test.com",
        nombre="Usuario",
        apellido="Sin Permisos",
        dni="20000002",
        password="hash-de-prueba",
        activo=True,
        role_id=rol_sin_permisos.id,
    )

    persona_general = Personal(
        dni="30000001",
        nombre="Ana",
        apellido="General",
        personnel_type_id=tipo_personal.id,
        sector_id=sector.id,
        menu_type_id=menu_general.id,
        activo=True,
    )

    persona_celiaca = Personal(
        dni="30000002",
        nombre="Lucía",
        apellido="Celíaca",
        personnel_type_id=tipo_personal.id,
        sector_id=sector.id,
        menu_type_id=menu_celiaco.id,
        activo=True,
    )

    db.session.add_all([
        usuario,
        usuario_sin_permisos,
        persona_general,
        persona_celiaca,
    ])
    db.session.flush()

    carga = Carga(
        creado_por=usuario.id,
        periodicidad="diaria",
        fecha_desde=FECHA_PEDIDO,
        fecha_hasta=FECHA_PEDIDO,
    )
    db.session.add(carga)
    db.session.flush()

    pedido = Pedido(
        carga_id=carga.id,
        sector_id=sector.id,
        fecha=FECHA_PEDIDO,
        tipo_comida_id=comida.id,
        estado="autorizado",
        creado_por=usuario.id,
    )
    db.session.add(pedido)
    db.session.flush()

    solicitud_general = SolicitudPedido(
        pedido_id=pedido.id,
        person_id=persona_general.id,
        tipo_comida_id=comida.id,
        tipo_menu_id=menu_general.id,
        condicion="regular",
    )

    solicitud_celiaca = SolicitudPedido(
        pedido_id=pedido.id,
        person_id=persona_celiaca.id,
        tipo_comida_id=comida.id,
        tipo_menu_id=menu_celiaco.id,
        condicion="regular",
    )

    db.session.add_all([solicitud_general, solicitud_celiaca])
    db.session.flush()

    db.session.add_all([
        Autorizacion(
            solicitud_id=solicitud_general.id,
            autorizada=False,
            usuario_id=usuario.id,
        ),
        Autorizacion(
            solicitud_id=solicitud_celiaca.id,
            autorizada=True,
            usuario_id=usuario.id,
        ),
    ])

    db.session.commit()

    return {
        "usuario": usuario,
        "usuario_sin_permisos": usuario_sin_permisos,
    }


@pytest.mark.parametrize(
    "url",
    [URL_REQUESTS, URL_AUTHORIZATIONS],
)
def test_sin_sesion_responde_401(app, url):
    respuesta = app.test_client().get(url)

    assert respuesta.status_code == 401


@pytest.mark.parametrize(
    "url",
    [URL_REQUESTS, URL_AUTHORIZATIONS],
)
def test_sin_permiso_responde_403(app, datos, url):
    client = crear_cliente_con_sesion(
        app,
        datos["usuario_sin_permisos"],
    )

    respuesta = client.get(url)

    assert respuesta.status_code == 403


def test_resumen_pedidos_filtrado_por_menu_cuenta_solo_ese_menu(app, datos):
    client = crear_cliente_con_sesion(app, datos["usuario"])

    respuesta = client.get(
        URL_REQUESTS,
        query_string={"tipo_menu": "Celíaco"},
    )

    assert respuesta.status_code == 200

    cuerpo = respuesta.get_json()
    assert cuerpo["pedidos_considerados"] == 1
    assert cuerpo["resultados"] == {
        "total": {"cantidad": 1},
    }


def test_resumen_autorizaciones_filtrado_por_menu_cuenta_solo_ese_menu(
    app,
    datos,
):
    client = crear_cliente_con_sesion(app, datos["usuario"])

    respuesta = client.get(
        URL_AUTHORIZATIONS,
        query_string={"tipo_menu": "Celíaco"},
    )

    assert respuesta.status_code == 200

    cuerpo = respuesta.get_json()
    assert cuerpo["pedidos_considerados"] == 1
    assert cuerpo["resultados"] == {
        "total": {
            "pedidas": 1,
            "autorizadas": 1,
            "diferencia": 0,
        },
    }