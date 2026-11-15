"""Tests de la consulta de comidas autorizadas (usan una base SQLite en memoria)."""
from datetime import date

import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role
from src.core.configuration.models import ID_CONFIGURACION, Configuration
from src.core.deliveries import (
    buscar_comidas_autorizadas,
    comidas_autorizadas_de,
    datos_comida_autorizada,
)
from src.core.deliveries.models import Entrega, EntregaDetalle
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.paginacion import paginar
from src.core.pedidos.models import Autorizacion, Carga, Pedido, SolicitudPedido
from src.core.personnel.models import Personal
from src.core.personnel_types.models import PersonnelType
from src.core.sectors.models import Sector
from src.core.users.models import User

FECHA = date(2026, 10, 13)
OTRA_FECHA = date(2026, 10, 14)


@pytest.fixture
def app(monkeypatch):
    """App con base en memoria y todas las tablas creadas."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def datos(app):
    """Crea sectores, comidas, menú, un usuario y dos personas."""
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
    rol = Role(name="Servicio de Alimentación")
    tipo_personal = PersonnelType(nombre="Personal Fijo")
    menu = MenuType(nombre="Vegetariano")
    almuerzo = FoodType(nombre="Almuerzo")
    cena = FoodType(nombre="Cena")
    db.session.add_all([guardia, pediatria, rol, tipo_personal, menu, almuerzo, cena])
    db.session.flush()

    usuario = User(
        email="alimentacion@test.com",
        nombre="Usuario",
        apellido="Prueba",
        dni="20000001",
        password="hash-de-prueba",
        activo=True,
        role_id=rol.id,
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
    db.session.add_all([usuario, ana, luis])
    db.session.commit()

    return {
        "guardia": guardia,
        "pediatria": pediatria,
        "menu": menu,
        "almuerzo": almuerzo,
        "cena": cena,
        "usuario": usuario,
        "ana": ana,
        "luis": luis,
    }


def crear_solicitud(datos, persona, sector, fecha, comida, estado="autorizado", autorizada=True):
    """Crea pedido, solicitud y (si ``autorizada`` no es None) su autorización, directo con los modelos.

    No usa la API de autorizaciones porque hoy da 500 (issue #13).
    """
    usuario = datos["usuario"]
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
            estado=estado,
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

    if autorizada is not None:
        db.session.add(Autorizacion(
            solicitud_id=solicitud.id,
            autorizada=autorizada,
            usuario_id=usuario.id,
        ))
    db.session.commit()
    return solicitud


def entregar(datos, solicitud):
    """Registra la entrega de una solicitud, directo con los modelos."""
    entrega = Entrega(
        usuario_id=datos["usuario"].id,
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


def ids_de_personas(consulta):
    """Devuelve los ids de persona de cada fila de la consulta, en orden."""
    return [solicitud.person_id for solicitud in consulta.all()]


# buscar_comidas_autorizadas

def test_autorizada_aparece_con_sus_datos(datos):
    crear_solicitud(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"])

    filas = buscar_comidas_autorizadas(fecha=FECHA).all()

    assert len(filas) == 1
    item = datos_comida_autorizada(filas[0])
    assert item["fecha"] == "2026-10-13"
    assert item["persona"]["dni"] == "30000001"
    assert item["persona"]["activo"] is True
    assert item["tipo_comida"]["nombre"] == "Almuerzo"
    assert item["tipo_menu"]["nombre"] == "Vegetariano"
    assert item["condicion"] == "regular"
    assert item["sector"]["nombre"] == "Guardia"
    assert item["entregada"] is False


def test_no_aparecen_rechazadas_ni_sin_autorizar(datos):
    # Pedido rechazado (sin autorizaciones).
    crear_solicitud(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"],
                    estado="rechazado", autorizada=None)
    # Pedido autorizado, pero esta solicitud no se autorizó.
    crear_solicitud(datos, datos["luis"], datos["pediatria"], FECHA, datos["almuerzo"],
                    autorizada=False)
    # Pedido todavía confirmado, sin revisar.
    crear_solicitud(datos, datos["ana"], datos["guardia"], FECHA, datos["cena"],
                    estado="confirmado", autorizada=None)

    assert buscar_comidas_autorizadas(fecha=FECHA).all() == []


def test_filtros(datos):
    ana, luis = datos["ana"], datos["luis"]
    crear_solicitud(datos, ana, datos["guardia"], FECHA, datos["almuerzo"])
    crear_solicitud(datos, ana, datos["guardia"], OTRA_FECHA, datos["cena"])
    crear_solicitud(datos, luis, datos["pediatria"], FECHA, datos["cena"])

    assert ids_de_personas(buscar_comidas_autorizadas(fecha=OTRA_FECHA)) == [ana.id]
    assert ids_de_personas(buscar_comidas_autorizadas(dni="30000002")) == [luis.id]
    assert ids_de_personas(buscar_comidas_autorizadas(dni="3000000")) == []
    assert ids_de_personas(buscar_comidas_autorizadas(nombre="ana gó")) == [ana.id, ana.id]
    assert ids_de_personas(buscar_comidas_autorizadas(nombre="LUIS")) == [luis.id]
    assert ids_de_personas(
        buscar_comidas_autorizadas(sector_id=datos["pediatria"].id)
    ) == [luis.id]
    assert ids_de_personas(
        buscar_comidas_autorizadas(tipo_comida_id=datos["cena"].id)
    ) == [luis.id, ana.id]
    assert ids_de_personas(
        buscar_comidas_autorizadas(fecha=FECHA, tipo_comida_id=datos["cena"].id)
    ) == [luis.id]


def test_entregada_y_no_entregada(datos):
    de_ana = crear_solicitud(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"])
    crear_solicitud(datos, datos["luis"], datos["pediatria"], FECHA, datos["almuerzo"])
    entregar(datos, de_ana)

    items = [datos_comida_autorizada(s) for s in buscar_comidas_autorizadas(fecha=FECHA)]
    entregadas = {item["persona"]["dni"]: item["entregada"] for item in items}

    assert entregadas == {"30000001": True, "30000002": False}


def test_dos_autorizaciones_misma_persona_se_entrega_una(datos):
    ana = datos["ana"]
    de_guardia = crear_solicitud(datos, ana, datos["guardia"], FECHA, datos["almuerzo"])
    crear_solicitud(datos, ana, datos["pediatria"], FECHA, datos["almuerzo"])
    entregar(datos, de_guardia)

    items = [datos_comida_autorizada(s) for s in buscar_comidas_autorizadas(dni=ana.dni)]

    assert len(items) == 2
    assert [item["entregada"] for item in items] == [True, True]


def test_pendientes_no_trae_las_entregadas(datos):
    de_ana = crear_solicitud(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"])
    crear_solicitud(datos, datos["luis"], datos["pediatria"], FECHA, datos["almuerzo"])
    entregar(datos, de_ana)

    pendientes = buscar_comidas_autorizadas(fecha=FECHA, pendientes=True).all()

    assert [s.person_id for s in pendientes] == [datos["luis"].id]


def test_pendientes_es_por_autorizacion(datos):
    # Ana tiene el almuerzo autorizado por dos sectores y retiró el de Guardia:
    # el de Pediatría sigue pendiente (aunque su marca "entregada" sea True).
    ana = datos["ana"]
    de_guardia = crear_solicitud(datos, ana, datos["guardia"], FECHA, datos["almuerzo"])
    de_pediatria = crear_solicitud(datos, ana, datos["pediatria"], FECHA, datos["almuerzo"])
    entregar(datos, de_guardia)

    pendientes = buscar_comidas_autorizadas(dni=ana.dni, pendientes=True).all()

    assert [s.id for s in pendientes] == [de_pediatria.id]


def test_persona_inactiva_aparece(datos):
    ana = datos["ana"]
    crear_solicitud(datos, ana, datos["guardia"], FECHA, datos["almuerzo"])
    ana.activo = False
    db.session.commit()

    filas = buscar_comidas_autorizadas(fecha=FECHA).all()

    assert len(filas) == 1
    assert datos_comida_autorizada(filas[0])["persona"]["activo"] is False


def test_se_puede_paginar(datos):
    db.session.add(Configuration(id=ID_CONFIGURACION, elementos_por_pagina=1, mantenimiento_activo=False))
    db.session.commit()
    crear_solicitud(datos, datos["ana"], datos["guardia"], FECHA, datos["almuerzo"])
    crear_solicitud(datos, datos["luis"], datos["pediatria"], FECHA, datos["almuerzo"])

    pagina = paginar(buscar_comidas_autorizadas(fecha=FECHA), 1)

    assert len(pagina.items) == 1
    assert pagina.total == 2


# comidas_autorizadas_de

def test_comidas_de_una_persona_en_una_fecha(datos):
    ana = datos["ana"]
    crear_solicitud(datos, ana, datos["guardia"], FECHA, datos["almuerzo"])
    crear_solicitud(datos, ana, datos["guardia"], FECHA, datos["cena"])
    crear_solicitud(datos, ana, datos["guardia"], OTRA_FECHA, datos["almuerzo"])
    crear_solicitud(datos, datos["luis"], datos["pediatria"], FECHA, datos["almuerzo"])

    comidas = comidas_autorizadas_de(ana.id, FECHA)

    assert [s.food_type.nombre for s in comidas] == ["Almuerzo", "Cena"]
    assert all(s.person_id == ana.id for s in comidas)


def test_comidas_de_sin_fecha_usa_hoy(datos, monkeypatch):
    ana = datos["ana"]
    crear_solicitud(datos, ana, datos["guardia"], FECHA, datos["almuerzo"])
    crear_solicitud(datos, ana, datos["guardia"], OTRA_FECHA, datos["cena"])
    monkeypatch.setattr("src.core.deliveries.hoy", lambda: OTRA_FECHA)

    comidas = comidas_autorizadas_de(ana.id)

    assert [s.food_type.nombre for s in comidas] == ["Cena"]


def test_comidas_de_persona_inexistente(datos):
    with pytest.raises(LookupError):
        comidas_autorizadas_de(9999, FECHA)
