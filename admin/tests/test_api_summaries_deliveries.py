"""Tests de GET /api/summaries/deliveries.

Usan una base SQLite en memoria y el cliente de pruebas de Flask, igual que
``test_api_entregas_resumen.py``. Pedidos, autorizaciones y entregas se
crean directo con los modelos.
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

MARTES = date(2026, 10, 13)
LUNES = date(2026, 10, 12)
SEPTIEMBRE = date(2026, 9, 30)  # Miércoles: su semana empieza el 28/09.
URL = "/api/summaries/deliveries"


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
    """Crea un usuario de Servicio de Alimentación (con ``summary_deliveries``),
    uno del Comedor (solo con ``delivery_index``), dos sectores, Almuerzo,
    Cena, dos tipos de menú y dos personas."""
    summary_deliveries = Permission(name="summary_deliveries")
    delivery_index = Permission(name="delivery_index")
    alimentacion = Role(
        name="Servicio de Alimentación", permissions=[summary_deliveries]
    )
    comedor = Role(name="Sector Comedor", permissions=[delivery_index])
    guardia = Sector(nombre="Guardia", descripcion="Sector de prueba", activo=True)
    pediatria = Sector(
        nombre="Pediatría", descripcion="Sector de prueba", activo=True
    )
    tipo_personal = PersonnelType(nombre="Personal Fijo")
    vegetariano = MenuType(nombre="Vegetariano")
    general = MenuType(nombre="General")
    almuerzo = FoodType(nombre="Almuerzo")
    cena = FoodType(nombre="Cena")
    db.session.add_all([
        alimentacion, comedor, guardia, pediatria,
        tipo_personal, vegetariano, general, almuerzo, cena,
    ])
    db.session.flush()

    usuario_alimentacion = crear_usuario(
        "alimentacion@test.com", "20000001", alimentacion
    )
    usuario_comedor = crear_usuario("comedor@test.com", "20000002", comedor)
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
        "usuario_alimentacion": usuario_alimentacion,
        "usuario_comedor": usuario_comedor,
        "guardia": guardia,
        "pediatria": pediatria,
        "vegetariano": vegetariano,
        "general": general,
        "almuerzo": almuerzo,
        "cena": cena,
        "ana": ana,
        "luis": luis,
    }


def crear_autorizacion(
    datos, persona, sector, fecha, comida, menu, autorizada=True
):
    """Crea pedido, solicitud y autorización de ``persona``, directo con los modelos.

    Reutiliza el pedido si ya existe, porque solo puede haber uno por sector,
    fecha y comida. Devuelve la ``Autorizacion`` creada.
    """
    usuario = datos["usuario_alimentacion"]
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
        autorizada=autorizada,
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


def cliente_con_sesion(app, usuario):
    """Devuelve un cliente de pruebas con la sesión de ``usuario`` iniciada."""
    client = app.test_client()
    with client.session_transaction() as session:
        session["user"] = usuario.email
        session["user_id"] = usuario.id
    return client


@pytest.fixture
def alimentacion(app, datos):
    """Cliente logueado como usuario de Servicio de Alimentación."""
    return cliente_con_sesion(app, datos["usuario_alimentacion"])


@pytest.fixture
def escenario(datos):
    """Cuatro comidas autorizadas (dos entregadas) y una no autorizada.

    - Ana, Almuerzo del martes, pedido de Guardia, Vegetariano: entregada.
    - Luis, Almuerzo del martes, mismo pedido de Guardia, General.
    - Ana, Cena del lunes, Guardia, Vegetariano: entregada.
    - Luis, Almuerzo de septiembre, Pediatría, General.
    - Luis, Cena del martes, Pediatría: no autorizada (no cuenta).
    """
    d = datos
    entregar(d, crear_autorizacion(
        d, d["ana"], d["guardia"], MARTES, d["almuerzo"], d["vegetariano"]
    ))
    crear_autorizacion(
        d, d["luis"], d["guardia"], MARTES, d["almuerzo"], d["general"]
    )
    entregar(d, crear_autorizacion(
        d, d["ana"], d["guardia"], LUNES, d["cena"], d["vegetariano"]
    ))
    crear_autorizacion(
        d, d["luis"], d["pediatria"], SEPTIEMBRE, d["almuerzo"], d["general"]
    )
    crear_autorizacion(
        d, d["luis"], d["pediatria"], MARTES, d["cena"], d["general"],
        autorizada=False,
    )
    return d


def cantidades(autorizadas, entregadas):
    """Arma el valor esperado de un grupo."""
    return {
        "autorizadas": autorizadas,
        "entregadas": entregadas,
        "diferencia": autorizadas - entregadas,
    }


# Acceso

def test_sin_sesion_responde_401(app):
    """Sin sesión responde 401."""
    assert app.test_client().get(URL).status_code == 401


def test_comedor_sin_permiso_responde_403(app, datos):
    """El Comedor tiene ``delivery_index`` pero no ``summary_deliveries``."""
    client = cliente_con_sesion(app, datos["usuario_comedor"])

    assert client.get(URL).status_code == 403


def test_servicio_de_alimentacion_puede_verlo(alimentacion):
    """Servicio de Alimentación tiene ``summary_deliveries``."""
    assert alimentacion.get(URL).status_code == 200


# Validación del query string

@pytest.mark.parametrize("parametros, campo", [
    ({"estado": "autorizado"}, "estado"),
    ({"page": "1"}, "page"),
    ({"fecha_desde": "13/10/2026"}, "fecha_desde"),
    ({"fecha_hasta": "2026-13-01"}, "fecha_hasta"),
    ({"sector_id": "abc"}, "sector_id"),
    ({"sector_id": "0"}, "sector_id"),
    ({"agrupamiento": "anio"}, "agrupamiento"),
])
def test_parametro_invalido_responde_400(alimentacion, parametros, campo):
    """Parámetros desconocidos o con formato inválido responden 400 con el campo."""
    respuesta = alimentacion.get(URL, query_string=parametros)

    assert respuesta.status_code == 400
    assert campo in respuesta.get_json()["campos"]


def test_fecha_hasta_anterior_a_desde_responde_400(alimentacion):
    """``fecha_desde`` posterior a ``fecha_hasta`` responde 400."""
    respuesta = alimentacion.get(URL, query_string={
        "fecha_desde": "2026-10-13",
        "fecha_hasta": "2026-10-12",
    })

    assert respuesta.status_code == 400


@pytest.mark.parametrize("campo", ["tipo_comida", "tipo_menu"])
def test_comida_o_menu_inexistente_responde_400(alimentacion, campo):
    """Un nombre de comida o de menú que no existe responde 400."""
    respuesta = alimentacion.get(URL, query_string={campo: "Inexistente"})

    assert respuesta.status_code == 400


# Resultados

def test_sin_datos_devuelve_resultados_vacios(alimentacion):
    """Sin comidas autorizadas, ``resultados`` vacío y totales en 0."""
    cuerpo = alimentacion.get(URL).get_json()

    assert cuerpo == {
        "agrupamiento": "total",
        "resultados": {},
        "totales": cantidades(0, 0),
    }


def test_sin_agrupamiento_todo_en_total(alimentacion, escenario):
    """Sin agrupamiento cuenta todo en ``"total"``; la no autorizada no cuenta."""
    cuerpo = alimentacion.get(URL).get_json()

    assert cuerpo["agrupamiento"] == "total"
    assert cuerpo["resultados"] == {"total": cantidades(4, 2)}
    assert cuerpo["totales"] == cantidades(4, 2)


def test_agrupa_por_dia(alimentacion, escenario):
    """Agrupa por la fecha del pedido."""
    cuerpo = alimentacion.get(URL, query_string={"agrupamiento": "dia"}).get_json()

    assert cuerpo["agrupamiento"] == "dia"
    assert cuerpo["resultados"] == {
        "2026-10-13": cantidades(2, 1),
        "2026-10-12": cantidades(1, 1),
        "2026-09-30": cantidades(1, 0),
    }


def test_agrupa_por_semana_desde_el_lunes(alimentacion, escenario):
    """La clave de la semana es su lunes."""
    respuesta = alimentacion.get(URL, query_string={"agrupamiento": "semana"})

    assert respuesta.get_json()["resultados"] == {
        "2026-10-12": cantidades(3, 2),
        "2026-09-28": cantidades(1, 0),
    }


def test_agrupa_por_mes(alimentacion, escenario):
    """La clave del mes es ``AAAA-MM``."""
    respuesta = alimentacion.get(URL, query_string={"agrupamiento": "mes"})

    assert respuesta.get_json()["resultados"] == {
        "2026-10": cantidades(3, 2),
        "2026-09": cantidades(1, 0),
    }


def test_agrupa_por_sector_del_pedido(alimentacion, escenario):
    """Agrupa por el sector que hizo el pedido, no el de la persona."""
    respuesta = alimentacion.get(URL, query_string={"agrupamiento": "sector"})

    assert respuesta.get_json()["resultados"] == {
        str(escenario["guardia"].id): cantidades(3, 2),
        str(escenario["pediatria"].id): cantidades(1, 0),
    }


def test_agrupa_por_comida_y_por_menu(alimentacion, escenario):
    """Las claves son los nombres de la comida o del menú."""
    por_comida = alimentacion.get(URL, query_string={"agrupamiento": "comida"})
    por_menu = alimentacion.get(URL, query_string={"agrupamiento": "menu"})

    assert por_comida.get_json()["resultados"] == {
        "Almuerzo": cantidades(3, 1),
        "Cena": cantidades(1, 1),
    }
    assert por_menu.get_json()["resultados"] == {
        "Vegetariano": cantidades(2, 2),
        "General": cantidades(2, 0),
    }


def test_filtro_por_rango_de_fechas(alimentacion, escenario):
    """El rango deja afuera las fechas que no entran."""
    respuesta = alimentacion.get(URL, query_string={
        "fecha_desde": "2026-10-01",
        "fecha_hasta": "2026-10-12",
    })

    assert respuesta.get_json()["totales"] == cantidades(1, 1)


def test_filtro_por_sector(alimentacion, escenario):
    """``sector_id`` filtra por el sector del pedido."""
    respuesta = alimentacion.get(
        URL, query_string={"sector_id": escenario["pediatria"].id}
    )

    assert respuesta.get_json()["totales"] == cantidades(1, 0)


def test_filtro_por_comida_sin_distinguir_mayusculas(alimentacion, escenario):
    """``tipo_comida`` es el nombre, sin distinguir mayúsculas."""
    respuesta = alimentacion.get(URL, query_string={"tipo_comida": "almuerzo"})

    assert respuesta.status_code == 200
    assert respuesta.get_json()["totales"] == cantidades(3, 1)


def test_filtro_por_menu_cuenta_solo_esas_solicitudes(alimentacion, escenario):
    """El almuerzo del martes tiene un Vegetariano y un General en el mismo
    pedido: filtrando por Vegetariano solo cuenta el de Ana."""
    respuesta = alimentacion.get(URL, query_string={"tipo_menu": "vegetariano"})

    assert respuesta.get_json()["totales"] == cantidades(2, 2)
