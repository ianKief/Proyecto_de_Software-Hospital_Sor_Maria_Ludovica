"""Tests de POST /api/deliveries.

Usan una base SQLite en memoria y el cliente de pruebas de Flask, igual que
``test_api_comidas_autorizadas.py``. La hora de Entregas se fija en el
13/10/2026 a las 12:00 (turno de Almuerzo), igual que los tests de E5.
"""
from datetime import date, datetime

import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Permission, Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.deliveries.models import Entrega
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
MEDIODIA = datetime(2026, 10, 13, 12, 0, tzinfo=ZONA_ARGENTINA)
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
def al_mediodia(monkeypatch):
    """Fija la hora de Entregas en el 13/10/2026 a las 12:00 (turno de Almuerzo)."""
    monkeypatch.setattr("src.core.deliveries.hora_actual", lambda: MEDIODIA)


@pytest.fixture
def datos(app, al_mediodia):
    """Crea un usuario del Comedor (con ``delivery_new``), uno del Servicio de
    Alimentación (sin ese permiso), Almuerzo, Cena y dos personas."""
    delivery_new = Permission(name="delivery_new")
    comedor = Role(name="Sector Comedor", permissions=[delivery_new])
    alimentacion = Role(name="Servicio de Alimentación")
    guardia = Sector(
        nombre="Guardia",
        descripcion="Sector de prueba",
        activo=True,
    )
    tipo_personal = PersonnelType(nombre="Personal Fijo")
    menu = MenuType(nombre="Vegetariano")
    almuerzo = FoodType(nombre="Almuerzo")
    cena = FoodType(nombre="Cena")
    db.session.add_all([
        comedor, alimentacion, guardia, tipo_personal, menu, almuerzo, cena,
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
    usuario_alimentacion = User(
        email="alimentacion@test.com",
        nombre="Usuario",
        apellido="Alimentación",
        dni="20000002",
        password="hash-de-prueba",
        activo=True,
        role_id=alimentacion.id,
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
    db.session.add_all([usuario_comedor, usuario_alimentacion, ana, luis])
    db.session.commit()

    return {
        "usuario_comedor": usuario_comedor,
        "usuario_alimentacion": usuario_alimentacion,
        "guardia": guardia,
        "menu": menu,
        "almuerzo": almuerzo,
        "cena": cena,
        "ana": ana,
        "luis": luis,
    }


def autorizar(datos, persona, comida):
    """Crea (o reutiliza) el pedido autorizado de la comida y una solicitud autorizada.

    Se reutiliza porque solo puede haber un pedido por sector, fecha y comida.
    """
    usuario = datos["usuario_comedor"]
    pedido = Pedido.query.filter_by(
        fecha=FECHA,
        tipo_comida_id=comida.id,
    ).first()
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
    db.session.add(Autorizacion(
        solicitud_id=solicitud.id,
        autorizada=True,
        usuario_id=usuario.id,
    ))
    db.session.commit()


def cuerpo_entrega(datos, personas, comida=None, responsable=None):
    """Arma el JSON que mandaría el Comedor.

    Sin ``responsable`` retira la primera persona. Con la lista vacía no se
    manda responsable, para que el error sea el de ``personas``.
    """
    cuerpo = {
        "personas": [persona.id for persona in personas],
        "tipo_comida_id": (comida or datos["almuerzo"]).id,
    }
    if responsable is None and personas:
        responsable = personas[0]
    if responsable is not None:
        cuerpo["responsable_id"] = responsable.id
    return cuerpo


@pytest.fixture
def comedor(app, datos):
    """Cliente logueado como usuario del Sector Comedor (con ``delivery_new``)."""
    return cliente_con_token(app, datos["usuario_comedor"])


# Acceso

def test_sin_token_responde_401(app):
    """Sin token responde 401."""
    client = app.test_client()

    assert client.post(URL, json={}).status_code == 401


def test_rol_sin_permiso_responde_403(app, datos):
    """El Servicio de Alimentación no tiene ``delivery_new``: responde 403."""
    client = cliente_con_token(app, datos["usuario_alimentacion"])

    respuesta = client.post(URL, json=cuerpo_entrega(datos, [datos["ana"]]))

    assert respuesta.status_code == 403
    assert Entrega.query.count() == 0


# Validación del cuerpo

def test_cuerpo_no_json_responde_400(comedor):
    """Un cuerpo que no es JSON válido responde 400."""
    respuesta = comedor.post(
        URL,
        data="esto no es json",
        content_type="application/json",
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json() == {
        "error": "El cuerpo debe ser JSON válido",
        "campos": [],
    }


def test_usuario_del_cliente_se_rechaza(comedor, datos):
    """El usuario sale del token: si el cliente lo manda, responde 400."""
    cuerpo = cuerpo_entrega(datos, [datos["ana"]])
    cuerpo["usuario_id"] = datos["usuario_comedor"].id

    respuesta = comedor.post(URL, json=cuerpo)

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["usuario_id"]


def test_sin_personas_responde_400(comedor, datos):
    """Una lista de personas vacía no pasa la validación."""
    respuesta = comedor.post(URL, json=cuerpo_entrega(datos, []))

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["personas"]


# Reglas de negocio

def test_cena_antes_de_su_horario_responde_201(comedor, datos):
    """Al mediodía se puede entregar la Cena: su horario todavía no terminó (EN3)."""
    autorizar(datos, datos["ana"], datos["cena"])

    respuesta = comedor.post(
        URL,
        json=cuerpo_entrega(datos, [datos["ana"]], comida=datos["cena"]),
    )

    assert respuesta.status_code == 201
    assert respuesta.get_json()["tipo_comida"]["nombre"] == "Cena"


def test_comida_terminada_responde_400(comedor, datos, monkeypatch):
    """A las 15:01 ya terminó el Almuerzo (11:30 a 15:00): responde 400 (EN3)."""
    pasadas_las_tres = datetime(2026, 10, 13, 15, 1, tzinfo=ZONA_ARGENTINA)
    monkeypatch.setattr("src.core.deliveries.hora_actual", lambda: pasadas_las_tres)
    autorizar(datos, datos["ana"], datos["almuerzo"])

    respuesta = comedor.post(URL, json=cuerpo_entrega(datos, [datos["ana"]]))

    assert respuesta.status_code == 400
    assert respuesta.get_json() == {
        "error": "El horario de Almuerzo terminó a las 15:00",
    }
    assert Entrega.query.count() == 0


def test_persona_sin_autorizacion_responde_400(comedor, datos):
    """Si alguna persona no tiene autorización no se guarda nada."""
    autorizar(datos, datos["ana"], datos["almuerzo"])

    respuesta = comedor.post(
        URL,
        json=cuerpo_entrega(datos, [datos["ana"], datos["luis"]]),
    )

    assert respuesta.status_code == 400
    assert "Sin autorización" in respuesta.get_json()["error"]
    assert Entrega.query.count() == 0


def test_ya_entregada_responde_409(comedor, datos):
    """La misma comida no se entrega dos veces: el segundo POST responde 409."""
    autorizar(datos, datos["ana"], datos["almuerzo"])
    cuerpo = cuerpo_entrega(datos, [datos["ana"]])

    assert comedor.post(URL, json=cuerpo).status_code == 201
    respuesta = comedor.post(URL, json=cuerpo)

    assert respuesta.status_code == 409
    assert "Ya retiraron" in respuesta.get_json()["error"]
    assert Entrega.query.count() == 1


# Entrega registrada

def test_entrega_valida_responde_201(comedor, datos):
    """Registra la entrega y devuelve fecha y hora, usuario, responsable y personas."""
    autorizar(datos, datos["ana"], datos["almuerzo"])
    autorizar(datos, datos["luis"], datos["almuerzo"])

    respuesta = comedor.post(
        URL,
        json=cuerpo_entrega(
            datos,
            [datos["ana"], datos["luis"]],
            responsable=datos["luis"],
        ),
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.get_json()
    assert cuerpo["fecha_hora"] == "2026-10-13T12:00:00-03:00"
    assert cuerpo["usuario"] == {
        "id": datos["usuario_comedor"].id,
        "email": "comedor@test.com",
    }
    assert cuerpo["responsable"]["id"] == datos["luis"].id
    assert cuerpo["tipo_comida"]["nombre"] == "Almuerzo"
    assert sorted(p["dni"] for p in cuerpo["personas"]) == ["30000001", "30000002"]
    assert cuerpo["personas"][0]["tipo_menu"]["nombre"] == "Vegetariano"
    assert cuerpo["personas"][0]["sector"]["nombre"] == "Guardia"
    assert Entrega.query.count() == 1
    assert cuerpo["id"] == Entrega.query.one().id


# Responsable del retiro (EN1)

def test_una_persona_sin_responsable_responde_201(comedor, datos):
    """Con una sola persona y sin responsable, retira ella misma."""
    autorizar(datos, datos["ana"], datos["almuerzo"])
    cuerpo = {
        "personas": [datos["ana"].id],
        "tipo_comida_id": datos["almuerzo"].id,
    }

    respuesta = comedor.post(URL, json=cuerpo)

    assert respuesta.status_code == 201
    assert respuesta.get_json()["responsable"]["id"] == datos["ana"].id


def test_varias_personas_sin_responsable_responde_400(comedor, datos):
    """Con varias personas el responsable es obligatorio."""
    autorizar(datos, datos["ana"], datos["almuerzo"])
    autorizar(datos, datos["luis"], datos["almuerzo"])
    cuerpo = cuerpo_entrega(datos, [datos["ana"], datos["luis"]])
    del cuerpo["responsable_id"]

    respuesta = comedor.post(URL, json=cuerpo)

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["responsable_id"]
    assert Entrega.query.count() == 0


def test_tercero_responde_201(comedor, datos):
    """Un tercero se registra con DNI y nombre, sin ``responsable_id``."""
    autorizar(datos, datos["ana"], datos["almuerzo"])
    autorizar(datos, datos["luis"], datos["almuerzo"])
    cuerpo = cuerpo_entrega(datos, [datos["ana"], datos["luis"]])
    del cuerpo["responsable_id"]
    cuerpo["responsable_dni"] = "30111222"
    cuerpo["responsable_nombre"] = "Juan Pérez"

    respuesta = comedor.post(URL, json=cuerpo)

    assert respuesta.status_code == 201
    assert respuesta.get_json()["responsable"] == {
        "id": None,
        "dni": "30111222",
        "nombre": "Juan Pérez",
        "apellido": None,
    }


def test_tercero_con_dni_invalido_responde_400(comedor, datos):
    """El DNI del tercero tiene que tener el formato de Personal."""
    autorizar(datos, datos["ana"], datos["almuerzo"])
    cuerpo = cuerpo_entrega(datos, [datos["ana"]])
    del cuerpo["responsable_id"]
    cuerpo["responsable_dni"] = "30.111.222"
    cuerpo["responsable_nombre"] = "Juan Pérez"

    respuesta = comedor.post(URL, json=cuerpo)

    assert respuesta.status_code == 400
    assert respuesta.get_json()["campos"] == ["responsable_dni"]
    assert Entrega.query.count() == 0


# Tipo de menú (EN2)

def test_tipo_menu_en_el_cuerpo_se_ignora(comedor, datos):
    """Si el cliente manda ``tipo_menu`` responde 201 y el menú sale de la solicitud."""
    autorizar(datos, datos["ana"], datos["almuerzo"])
    cuerpo = cuerpo_entrega(datos, [datos["ana"]])
    cuerpo["tipo_menu"] = "Otro menú"

    respuesta = comedor.post(URL, json=cuerpo)

    assert respuesta.status_code == 201
    persona = respuesta.get_json()["personas"][0]
    assert persona["tipo_menu"]["nombre"] == "Vegetariano"
