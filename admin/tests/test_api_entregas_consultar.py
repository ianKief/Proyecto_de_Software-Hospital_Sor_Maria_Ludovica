"""Tests de GET /api/deliveries y GET /api/deliveries/<id>.

Usan una base SQLite en memoria y el cliente de pruebas de Flask, igual que
``test_api_entregas_registrar.py``. Las entregas se crean directo con los
modelos; la hora de Entregas se fija con monkeypatch cuando hace falta.
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
FUERA_DE_TURNO = datetime(2026, 10, 13, 10, 30, tzinfo=ZONA_ARGENTINA)
URL = "/api/deliveries"


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


@pytest.fixture
def datos(app):
    """Crea un usuario del Comedor (con ``delivery_index`` y ``delivery_show``),
    uno sin permisos, dos sectores, Almuerzo, Cena y dos personas."""
    delivery_index = Permission(name="delivery_index")
    delivery_show = Permission(name="delivery_show")
    comedor = Role(name="Sector Comedor", permissions=[delivery_index, delivery_show])
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
    menu = MenuType(nombre="Vegetariano")
    almuerzo = FoodType(nombre="Almuerzo")
    cena = FoodType(nombre="Cena")
    db.session.add_all([
        comedor, sin_permisos, guardia, pediatria, tipo_personal, menu, almuerzo, cena,
    ])
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
        email="otro@test.com",
        nombre="Usuario",
        apellido="Sin Permisos",
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
        sector_id=pediatria.id,
        menu_type_id=menu.id,
        activo=True,
    )
    db.session.add_all([usuario_comedor, usuario_sin_permisos, ana, luis])
    db.session.commit()

    return {
        "usuario_comedor": usuario_comedor,
        "usuario_sin_permisos": usuario_sin_permisos,
        "guardia": guardia,
        "pediatria": pediatria,
        "menu": menu,
        "almuerzo": almuerzo,
        "cena": cena,
        "ana": ana,
        "luis": luis,
    }


def crear_entrega(datos, persona, sector, fecha, comida):
    """Crea pedido, solicitud y autorización de ``persona`` y la entrega, directo con los modelos.

    Reutiliza el pedido si ya existe, porque solo puede haber uno por sector,
    fecha y comida. Devuelve la ``Entrega`` creada.
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
        tipo_menu_id=datos["menu"].id,
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
    db.session.flush()

    entrega = Entrega(
        usuario_id=usuario.id,
        responsable_id=persona.id,
        tipo_comida_id=comida.id,
    )
    db.session.add(entrega)
    db.session.flush()
    db.session.add(EntregaDetalle(
        entrega_id=entrega.id,
        autorizacion_id=autorizacion.id,
    ))
    db.session.commit()
    return entrega


@pytest.fixture
def comedor(app, datos):
    """Cliente logueado como usuario del Sector Comedor."""
    return cliente_con_token(app, datos["usuario_comedor"])


def fijar_hora(monkeypatch, momento):
    """Fija la hora que usa el módulo de Entregas."""
    monkeypatch.setattr("src.core.deliveries.ahora", lambda: momento)


def ids_de_items(respuesta):
    """Devuelve los ids de las entregas de una respuesta paginada, ordenados."""
    return sorted(item["id"] for item in respuesta.get_json()["items"])


# Acceso

def test_sin_token_responde_401(app):
    """Sin token, listado y detalle responden 401."""
    client = app.test_client()

    assert client.get(URL).status_code == 401
    assert client.get(f"{URL}/1").status_code == 401


def test_rol_sin_permiso_responde_403(app, datos):
    """Un rol sin ``delivery_index`` ni ``delivery_show`` recibe 403."""
    client = cliente_con_token(app, datos["usuario_sin_permisos"])

    assert client.get(URL).status_code == 403
    assert client.get(f"{URL}/1").status_code == 403


# Validación del query string

def test_parametro_desconocido_responde_400(comedor):
    """Un parámetro que no es filtro ni ``page`` responde 400."""
    respuesta = comedor.get(URL, query_string={"usuario_id": "1"})

    assert respuesta.status_code == 400
    assert respuesta.get_json() == {
        "error": "Se recibieron parámetros no permitidos",
        "campos": ["usuario_id"],
    }


def test_fecha_invalida_responde_400(comedor):
    """Una fecha que no es AAAA-MM-DD responde 400."""
    respuesta = comedor.get(URL, query_string={"fecha": "13/10/2026"})

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["fecha"]


# Listado

def test_con_filtro_pagina_resultados(comedor, datos):
    """Con filtro devuelve solo lo que cumple, paginado según la configuración."""
    db.session.get(Configuration, ID_CONFIGURACION).elementos_por_pagina = 1
    db.session.commit()
    crear_entrega(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"])
    crear_entrega(datos, datos["ana"], datos["guardia"], FECHA, datos["cena"])
    crear_entrega(datos, datos["luis"], datos["pediatria"], FECHA, datos["almuerzo"])

    respuesta = comedor.get(
        URL,
        query_string={"sector_id": datos["guardia"].id, "page": "1"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert len(cuerpo["items"]) == 1
    assert cuerpo["items"][0]["personas"][0]["sector"]["nombre"] == "Guardia"
    assert cuerpo["pagina"] == 1
    assert cuerpo["por_pagina"] == 1
    assert cuerpo["total"] == 2
    assert cuerpo["paginas"] == 2


def test_sin_filtros_en_turno_lista_ese_turno_de_hoy(comedor, datos, monkeypatch):
    """A las 12:00 (Almuerzo), sin filtros solo aparecen los almuerzos de hoy."""
    fijar_hora(monkeypatch, MEDIODIA)
    almuerzo_hoy = crear_entrega(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"])
    crear_entrega(datos, datos["ana"], datos["guardia"], FECHA, datos["cena"])
    crear_entrega(datos, datos["luis"], datos["pediatria"], OTRA_FECHA, datos["almuerzo"])

    respuesta = comedor.get(URL)

    assert respuesta.status_code == 200
    assert ids_de_items(respuesta) == [almuerzo_hoy.id]


def test_sin_filtros_fuera_de_turno_lista_todas_las_de_hoy(comedor, datos, monkeypatch):
    """A las 10:30 no hay turno: sin filtros aparecen todas las comidas de hoy."""
    fijar_hora(monkeypatch, FUERA_DE_TURNO)
    almuerzo_hoy = crear_entrega(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"])
    cena_hoy = crear_entrega(datos, datos["ana"], datos["guardia"], FECHA, datos["cena"])
    crear_entrega(datos, datos["luis"], datos["pediatria"], OTRA_FECHA, datos["almuerzo"])

    respuesta = comedor.get(URL)

    assert respuesta.status_code == 200
    assert ids_de_items(respuesta) == sorted([almuerzo_hoy.id, cena_hoy.id])


# Detalle

def test_detalle_existente_responde_200(comedor, datos):
    """El detalle devuelve la entrega con sus datos."""
    entrega = crear_entrega(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"])

    respuesta = comedor.get(f"{URL}/{entrega.id}")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["id"] == entrega.id
    assert cuerpo["tipo_comida"]["nombre"] == "Almuerzo"
    assert cuerpo["responsable"]["dni"] == "30000001"
    assert [p["dni"] for p in cuerpo["personas"]] == ["30000001"]


def test_detalle_inexistente_responde_404(comedor):
    """Si la entrega no existe responde 404 con el mensaje de error."""
    respuesta = comedor.get(f"{URL}/9999")

    assert respuesta.status_code == 404
    assert respuesta.get_json() == {"error": "La entrega no existe"}
