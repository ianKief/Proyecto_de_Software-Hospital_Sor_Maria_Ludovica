"""Tests de GET /api/deliveries/summary.

Usan una base SQLite en memoria y el cliente de pruebas de Flask, igual que
``test_api_entregas_consultar.py``. Pedidos, autorizaciones y entregas se
crean directo con los modelos; "hoy" se fija con monkeypatch.
"""
from datetime import date, datetime

import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.deliveries.models import Entrega, EntregaDetalle
from src.core.deliveries.turnos import ZONA_ARGENTINA
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Autorizacion, Carga, Pedido, SolicitudPedido
from src.core.personnel.models import Personal
from src.core.personnel_types.models import PersonnelType
from src.core.sectors.models import Sector
from src.core.users.models import User
from tests.helpers_token import cliente_con_token

FECHA = date(2026, 10, 13)
OTRA_FECHA = date(2026, 10, 12)
MEDIODIA = datetime(2026, 10, 13, 12, 0, tzinfo=ZONA_ARGENTINA)
URL = "/api/deliveries/summary"


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
            elementos_por_pagina=25,
            mantenimiento_activo=False,
        ))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


def crear_usuario(email, dni, rol):
    """Crea (sin commit) un usuario activo con ese rol."""
    usuario = User(
        email=email,
        nombre="Usuario",
        apellido="De Prueba",
        dni=dni,
        password="hash-de-prueba",
        activo=True,
        role_id=rol.id,
    )
    db.session.add(usuario)
    return usuario


@pytest.fixture
def datos(app):
    """Crea usuarios del Comedor, de Servicio de Alimentación (los dos con
    ``delivery_index``) y uno sin permisos; dos sectores, Almuerzo, Cena,
    dos tipos de menú y dos personas."""
    delivery_index = Permission(name="delivery_index")
    comedor = Role(name="Sector Comedor", permissions=[delivery_index])
    alimentacion = Role(
        name="Servicio de Alimentación", permissions=[delivery_index]
    )
    sin_permisos = Role(name="Sin permisos")
    guardia = Sector(
        nombre="Guardia",
        descripcion="Sector de prueba",
        activo=True,
    )
    pediatria = Sector(
        nombre="Pediatría",
        descripcion="Sector de prueba",
        activo=True,
    )
    tipo_personal = PersonnelType(nombre="Personal Fijo")
    vegetariano = MenuType(nombre="Vegetariano")
    general = MenuType(nombre="General")
    almuerzo = FoodType(nombre="Almuerzo")
    cena = FoodType(nombre="Cena")
    db.session.add_all([
        comedor, alimentacion, sin_permisos, guardia, pediatria,
        tipo_personal, vegetariano, general, almuerzo, cena,
    ])
    db.session.flush()

    usuario_comedor = crear_usuario("comedor@test.com", "20000001", comedor)
    usuario_alimentacion = crear_usuario(
        "alimentacion@test.com", "20000002", alimentacion
    )
    usuario_sin_permisos = crear_usuario("otro@test.com", "20000003", sin_permisos)
    ana = Personal(
        dni="30000001",
        nombre="Ana",
        apellido="Gómez",
        personnel_type_id=tipo_personal.id,
        sector_id=guardia.id,
        menu_type_id=vegetariano.id,
        activo=True,
    )
    luis = Personal(
        dni="30000002",
        nombre="Luis",
        apellido="Pérez",
        personnel_type_id=tipo_personal.id,
        sector_id=pediatria.id,
        menu_type_id=general.id,
        activo=True,
    )
    db.session.add_all([ana, luis])
    db.session.commit()

    return {
        "usuario_comedor": usuario_comedor,
        "usuario_alimentacion": usuario_alimentacion,
        "usuario_sin_permisos": usuario_sin_permisos,
        "guardia": guardia,
        "pediatria": pediatria,
        "vegetariano": vegetariano,
        "general": general,
        "almuerzo": almuerzo,
        "cena": cena,
        "ana": ana,
        "luis": luis,
    }


def crear_autorizacion(datos, persona, sector, fecha, comida, menu):
    """Crea pedido, solicitud y autorización de ``persona``, directo con los modelos.

    Reutiliza el pedido si ya existe, porque solo puede haber uno por sector,
    fecha y comida. Devuelve la ``Autorizacion`` creada.
    """
    usuario = datos["usuario_comedor"]
    pedido = Pedido.query.filter_by(
        sector_id=sector.id, fecha=fecha, tipo_comida_id=comida.id
    ).first()
    if pedido is None:
        carga = Carga(
            creado_por=usuario.id,
            periodicidad="diaria",
            fecha_desde=fecha,
            fecha_hasta=fecha,
        )
        db.session.add(carga)
        db.session.flush()
        pedido = Pedido(
            carga_id=carga.id,
            sector_id=sector.id,
            fecha=fecha,
            tipo_comida_id=comida.id,
            estado="autorizado",
            creado_por=usuario.id,
        )
        db.session.add(pedido)
        db.session.flush()

    solicitud = SolicitudPedido(
        pedido_id=pedido.id,
        person_id=persona.id,
        tipo_comida_id=comida.id,
        tipo_menu_id=menu.id,
        condicion="regular",
    )
    db.session.add(solicitud)
    db.session.flush()
    autorizacion = Autorizacion(
        solicitud_id=solicitud.id,
        autorizada=True,
        usuario_id=usuario.id,
    )
    db.session.add(autorizacion)
    db.session.commit()
    return autorizacion


def entregar(datos, autorizacion):
    """Registra la entrega de ``autorizacion``, directo con los modelos."""
    solicitud = autorizacion.solicitud
    entrega = Entrega(
        usuario_id=datos["usuario_comedor"].id,
        responsable_id=solicitud.person_id,
        tipo_comida_id=solicitud.tipo_comida_id,
    )
    db.session.add(entrega)
    db.session.flush()
    db.session.add(EntregaDetalle(
        entrega_id=entrega.id,
        autorizacion_id=autorizacion.id,
    ))
    db.session.commit()


@pytest.fixture
def comedor(app, datos):
    """Cliente logueado como usuario del Sector Comedor."""
    return cliente_con_token(app, datos["usuario_comedor"])


def fijar_hoy(monkeypatch, momento):
    """Fija la hora que usa ``hoy()``.

    Se parchea en ``turnos`` porque ``hoy()`` llama a ``hora_actual`` de su
    propio módulo.
    """
    monkeypatch.setattr("src.core.deliveries.turnos.hora_actual", lambda: momento)


# Acceso

def test_sin_token_responde_401(app):
    """Sin token responde 401."""
    assert app.test_client().get(URL).status_code == 401


def test_rol_sin_permiso_responde_403(app, datos):
    """Un rol sin ``delivery_index`` recibe 403."""
    client = cliente_con_token(app, datos["usuario_sin_permisos"])

    assert client.get(URL).status_code == 403


def test_servicio_de_alimentacion_puede_verlo(app, datos):
    """Servicio de Alimentación también tiene ``delivery_index``."""
    client = cliente_con_token(app, datos["usuario_alimentacion"])

    respuesta = client.get(URL, query_string={"fecha": "2026-10-13"})

    assert respuesta.status_code == 200


# Validación del query string

def test_parametro_desconocido_responde_400(comedor):
    """Un parámetro que no es filtro responde 400."""
    respuesta = comedor.get(URL, query_string={"usuario_id": "1"})

    assert respuesta.status_code == 400
    assert respuesta.get_json() == {
        "error": "Se recibieron parámetros no permitidos",
        "campos": ["usuario_id"],
    }


def test_page_responde_400(comedor):
    """El resumen no se pagina: ``page`` responde 400."""
    respuesta = comedor.get(URL, query_string={"page": "1"})

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["page"]


def test_fecha_invalida_responde_400(comedor):
    """Una fecha que no es AAAA-MM-DD responde 400."""
    respuesta = comedor.get(URL, query_string={"fecha": "13/10/2026"})

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["fecha"]


# Resumen

def test_sin_filtros_resume_solo_hoy(comedor, datos, monkeypatch):
    """Sin filtros cuenta solo las comidas de hoy, de todas las comidas."""
    fijar_hoy(monkeypatch, MEDIODIA)
    vegetariano = datos["vegetariano"]
    crear_autorizacion(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"], vegetariano)
    crear_autorizacion(datos, datos["ana"], datos["guardia"], FECHA, datos["cena"], vegetariano)
    crear_autorizacion(datos, datos["ana"], datos["guardia"], OTRA_FECHA, datos["almuerzo"], vegetariano)

    respuesta = comedor.get(URL)

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["fecha"] == "2026-10-13"
    assert [(item["tipo_comida"], item["autorizadas"]) for item in cuerpo["items"]] == [
        ("Almuerzo", 1),
        ("Cena", 1),
    ]


def test_sin_datos_devuelve_lista_vacia(comedor, datos):
    """Si no hay autorizaciones, ``items`` vacío y totales en 0."""
    respuesta = comedor.get(URL, query_string={"fecha": "2026-10-13"})

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "fecha": "2026-10-13",
        "items": [],
        "totales": {"autorizadas": 0, "entregadas": 0, "diferencia": 0},
    }


def test_filtro_sector_sin_fecha_usa_hoy(comedor, datos, monkeypatch):
    """Con solo ``sector_id`` cuenta ese sector y, como no vino fecha, solo hoy."""
    fijar_hoy(monkeypatch, MEDIODIA)
    almuerzo = datos["almuerzo"]
    crear_autorizacion(datos, datos["ana"], datos["guardia"], FECHA, almuerzo, datos["vegetariano"])
    crear_autorizacion(datos, datos["ana"], datos["guardia"], OTRA_FECHA, almuerzo, datos["vegetariano"])
    crear_autorizacion(datos, datos["luis"], datos["pediatria"], FECHA, almuerzo, datos["general"])

    respuesta = comedor.get(URL, query_string={"sector_id": datos["guardia"].id})

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["fecha"] == "2026-10-13"
    assert cuerpo["items"] == [{
        "tipo_comida": "Almuerzo",
        "tipo_menu": "Vegetariano",
        "autorizadas": 1,
        "entregadas": 0,
        "diferencia": 1,
    }]


def test_agrupa_por_comida_y_menu_con_totales(comedor, datos):
    """Agrupa por comida y menú, ordenado, y los totales suman los ítems."""
    almuerzo, cena = datos["almuerzo"], datos["cena"]
    ana_almuerzo = crear_autorizacion(
        datos, datos["ana"], datos["guardia"], FECHA, almuerzo, datos["vegetariano"]
    )
    crear_autorizacion(datos, datos["ana"], datos["guardia"], FECHA, cena, datos["vegetariano"])
    luis_almuerzo = crear_autorizacion(
        datos, datos["luis"], datos["pediatria"], FECHA, almuerzo, datos["general"]
    )
    entregar(datos, ana_almuerzo)
    entregar(datos, luis_almuerzo)

    respuesta = comedor.get(URL, query_string={"fecha": "2026-10-13"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["items"] == [
        {"tipo_comida": "Almuerzo", "tipo_menu": "General",
         "autorizadas": 1, "entregadas": 1, "diferencia": 0},
        {"tipo_comida": "Almuerzo", "tipo_menu": "Vegetariano",
         "autorizadas": 1, "entregadas": 1, "diferencia": 0},
        {"tipo_comida": "Cena", "tipo_menu": "Vegetariano",
         "autorizadas": 1, "entregadas": 0, "diferencia": 1},
    ]
    assert cuerpo["totales"] == {"autorizadas": 3, "entregadas": 2, "diferencia": 1}


def test_filtro_tipo_comida(comedor, datos):
    """Con ``tipo_comida_id`` solo cuenta esa comida."""
    vegetariano = datos["vegetariano"]
    crear_autorizacion(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"], vegetariano)
    crear_autorizacion(datos, datos["ana"], datos["guardia"], FECHA, datos["cena"], vegetariano)

    respuesta = comedor.get(
        URL,
        query_string={"fecha": "2026-10-13", "tipo_comida_id": datos["cena"].id},
    )

    assert respuesta.status_code == 200
    assert [item["tipo_comida"] for item in respuesta.get_json()["items"]] == ["Cena"]


def test_dos_autorizaciones_una_retirada(comedor, datos):
    """Misma persona con dos almuerzos autorizados (dos sectores) y uno retirado:
    cuenta 2 autorizadas y 1 entregada."""
    almuerzo, vegetariano = datos["almuerzo"], datos["vegetariano"]
    por_guardia = crear_autorizacion(datos, datos["ana"], datos["guardia"], FECHA, almuerzo, vegetariano)
    crear_autorizacion(datos, datos["ana"], datos["pediatria"], FECHA, almuerzo, vegetariano)
    entregar(datos, por_guardia)

    respuesta = comedor.get(URL, query_string={"fecha": "2026-10-13"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["items"] == [{
        "tipo_comida": "Almuerzo",
        "tipo_menu": "Vegetariano",
        "autorizadas": 2,
        "entregadas": 1,
        "diferencia": 1,
    }]
    assert cuerpo["totales"] == {"autorizadas": 2, "entregadas": 1, "diferencia": 1}
