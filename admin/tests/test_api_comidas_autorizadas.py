"""Tests de GET /api/authorized-meals y /api/authorized-meals/<person_id>.

Usan una base SQLite en memoria y el cliente de pruebas de Flask, igual que
``test_api_configuration.py``. Se pagina de a 1 elemento para comprobar que
los totales cuentan todo el filtro y no solo la página.
"""
from datetime import date

import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.deliveries.models import Entrega, EntregaDetalle
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Autorizacion, Carga, Pedido, SolicitudPedido
from src.core.personnel.models import Personal
from src.core.personnel_types.models import PersonnelType
from src.core.sectors.models import Sector
from src.core.users.models import User

FECHA = date(2026, 10, 13)
URL = "/api/authorized-meals"


@pytest.fixture
def app(monkeypatch):
    """App con base en memoria, todas las tablas y 1 elemento por página."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        db.session.add(Configuration(
            id=ID_CONFIGURACION,
            elementos_por_pagina=1,
            mantenimiento_activo=False,
        ))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def datos(app):
    """Crea un usuario del Comedor con el permiso, otro sin permisos y dos personas."""
    permiso = Permission(name="authorized_meals_index")
    comedor = Role(name="Sector Comedor", permissions=[permiso])
    sin_permisos = Role(name="Jefe de Servicio")
    guardia = Sector(nombre="Guardia", activo=True)
    tipo_personal = PersonnelType(nombre="Personal Fijo")
    menu = MenuType(nombre="Vegetariano")
    almuerzo = FoodType(nombre="Almuerzo")
    db.session.add_all([comedor, sin_permisos, guardia, tipo_personal, menu, almuerzo])
    db.session.flush()

    usuario_comedor = User(
        email="comedor@test.com",
        nombre="Usuario",
        apellido="Comedor",
        dni="20000001",
        password="hash-de-prueba",
        activo=True,
        role_id=comedor.id,
    )
    usuario_sin_permisos = User(
        email="jefe@test.com",
        nombre="Usuario",
        apellido="Jefe",
        dni="20000002",
        password="hash-de-prueba",
        activo=True,
        role_id=sin_permisos.id,
    )
    ana = Personal(
        dni="30000001",
        nombre="Ana",
        apellido="Gómez",
        personnel_type_id=tipo_personal.id,
        sector_id=guardia.id,
        menu_type_id=menu.id,
        activo=True,
    )
    luis = Personal(
        dni="30000002",
        nombre="Luis",
        apellido="Pérez",
        personnel_type_id=tipo_personal.id,
        sector_id=guardia.id,
        menu_type_id=menu.id,
        activo=True,
    )
    db.session.add_all([usuario_comedor, usuario_sin_permisos, ana, luis])
    db.session.commit()

    return {
        "usuario_comedor": usuario_comedor,
        "usuario_sin_permisos": usuario_sin_permisos,
        "guardia": guardia,
        "menu": menu,
        "almuerzo": almuerzo,
        "ana": ana,
        "luis": luis,
    }


def crear_solicitud_autorizada(datos, persona):
    """Crea (o reutiliza) el pedido autorizado de Almuerzo y una solicitud autorizada."""
    usuario = datos["usuario_comedor"]
    pedido = Pedido.query.filter_by(fecha=FECHA).first()
    if pedido is None:
        carga = Carga(
            creado_por=usuario.id,
            periodicidad="diaria",
            fecha_desde=FECHA,
            fecha_hasta=FECHA,
        )
        db.session.add(carga)
        db.session.flush()
        pedido = Pedido(
            carga_id=carga.id,
            sector_id=datos["guardia"].id,
            fecha=FECHA,
            tipo_comida_id=datos["almuerzo"].id,
            estado="autorizado",
            creado_por=usuario.id,
        )
        db.session.add(pedido)
        db.session.flush()

    solicitud = SolicitudPedido(
        pedido_id=pedido.id,
        person_id=persona.id,
        tipo_comida_id=datos["almuerzo"].id,
        tipo_menu_id=datos["menu"].id,
        condicion="regular",
    )
    db.session.add(solicitud)
    db.session.flush()
    db.session.add(Autorizacion(
        solicitud_id=solicitud.id,
        autorizada=True,
        usuario_id=usuario.id,
    ))
    db.session.commit()
    return solicitud


def entregar(datos, solicitud):
    """Registra la entrega de una solicitud, directo con los modelos."""
    entrega = Entrega(
        usuario_id=datos["usuario_comedor"].id,
        responsable_id=solicitud.person_id,
        tipo_comida_id=solicitud.tipo_comida_id,
    )
    db.session.add(entrega)
    db.session.flush()
    db.session.add(EntregaDetalle(
        entrega_id=entrega.id,
        autorizacion_id=solicitud.autorizacion.id,
    ))
    db.session.commit()


def cliente_con_sesion(app, usuario):
    """Devuelve un cliente de pruebas con la sesión de ``usuario`` iniciada."""
    client = app.test_client()
    with client.session_transaction() as session:
        session["user"] = usuario.email
        session["user_id"] = usuario.id
    return client


@pytest.fixture
def comedor(app, datos):
    """Cliente logueado como usuario del Sector Comedor (con el permiso)."""
    return cliente_con_sesion(app, datos["usuario_comedor"])


# Acceso

def test_sin_sesion_responde_401(app):
    """Sin sesión, los dos endpoints responden 401."""
    client = app.test_client()

    assert client.get(f"{URL}?fecha=2026-10-13").status_code == 401
    assert client.get(f"{URL}/1").status_code == 401


def test_rol_sin_permiso_responde_403(app, datos):
    """Un rol sin ``authorized_meals_index`` recibe 403 en los dos endpoints."""
    client = cliente_con_sesion(app, datos["usuario_sin_permisos"])

    assert client.get(f"{URL}?fecha=2026-10-13").status_code == 403
    assert client.get(f"{URL}/{datos['ana'].id}").status_code == 403


# GET /api/authorized-meals

def test_sin_filtros_responde_400(comedor):
    """Sin ningún filtro (la página no cuenta) responde 400."""
    respuesta = comedor.get(f"{URL}?page=1")

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Debe indicar al menos un filtro"


def test_fecha_invalida_responde_400(comedor):
    """Una fecha que no es AAAA-MM-DD responde 400 indicando el campo."""
    respuesta = comedor.get(f"{URL}?fecha=13/10/2026")

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["fecha"]


@pytest.mark.parametrize("valor", ["abc", "0", "-1", "+5", "1_0"])
def test_id_invalido_responde_400(comedor, valor):
    """Un ``sector_id`` que no es entero positivo escrito solo con dígitos responde 400.

    ``"+5"`` y ``"1_0"`` los aceptaría ``int()``, pero no son ids válidos.
    Se usa ``query_string`` para que el cliente codifique el ``+`` como ``%2B``:
    escrito tal cual en la URL, ``+`` significa espacio.
    """
    respuesta = comedor.get(URL, query_string={"sector_id": valor})

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["sector_id"]


def test_parametro_desconocido_responde_400(comedor):
    """Un parámetro que no está en la lista permitida responde 400."""
    respuesta = comedor.get(f"{URL}?fecha=2026-10-13&fehca=2026-10-13")

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["fehca"]


def test_con_filtro_devuelve_items_y_totales(comedor, datos):
    """Con un filtro devuelve la página de ítems y los totales de todo el filtro."""
    solicitud_ana = crear_solicitud_autorizada(datos, datos["ana"])
    crear_solicitud_autorizada(datos, datos["luis"])
    entregar(datos, solicitud_ana)

    respuesta = comedor.get(f"{URL}?fecha=2026-10-13")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    # Se pagina de a 1: la página trae un ítem, pero hay 2 en total.
    assert len(cuerpo["items"]) == 1
    assert cuerpo["total"] == 2
    assert cuerpo["totales"] == {"autorizadas": 2, "entregadas": 1}
    # Orden por apellido: Gómez (Ana) primero, y ya retiró.
    assert cuerpo["items"][0]["persona"]["dni"] == "30000001"
    assert cuerpo["items"][0]["entregada"] is True


# GET /api/authorized-meals/<person_id>

def test_persona_con_fecha_devuelve_sus_comidas(comedor, datos):
    """Devuelve las comidas autorizadas de la persona en esa fecha."""
    crear_solicitud_autorizada(datos, datos["ana"])

    respuesta = comedor.get(f"{URL}/{datos['ana'].id}?fecha=2026-10-13")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["fecha"] == "2026-10-13"
    assert len(cuerpo["items"]) == 1
    assert cuerpo["items"][0]["tipo_comida"]["nombre"] == "Almuerzo"
    assert cuerpo["items"][0]["entregada"] is False


def test_persona_sin_fecha_usa_hoy(comedor, datos, monkeypatch):
    """Sin ``fecha`` usa la de hoy (se fija ``hoy()`` para que el test no dependa del reloj)."""
    monkeypatch.setattr("src.web.controllers.api_deliveries.hoy", lambda: FECHA)
    crear_solicitud_autorizada(datos, datos["ana"])

    respuesta = comedor.get(f"{URL}/{datos['ana'].id}")

    assert respuesta.status_code == 200
    assert respuesta.get_json()["fecha"] == "2026-10-13"
    assert len(respuesta.get_json()["items"]) == 1


def test_persona_fecha_invalida_responde_400(comedor, datos):
    """Una fecha inválida en la consulta por persona responde 400."""
    respuesta = comedor.get(f"{URL}/{datos['ana'].id}?fecha=ayer")

    assert respuesta.status_code == 400


def test_persona_inexistente_responde_404(comedor):
    """Si la persona no existe responde 404 en JSON."""
    respuesta = comedor.get(f"{URL}/99999?fecha=2026-10-13")

    assert respuesta.status_code == 404
    assert respuesta.get_json() == {"error": "La persona no existe"}
