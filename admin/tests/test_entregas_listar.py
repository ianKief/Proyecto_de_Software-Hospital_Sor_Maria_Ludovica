"""Tests de listar, obtener y resumir entregas (usan una base SQLite en memoria)."""
from datetime import date, datetime

import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role
from src.core.deliveries import (
    datos_entrega,
    listar_entregas,
    obtener_entrega,
    resumen_entregas,
)
from src.core.deliveries.models import Entrega, EntregaDetalle
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Autorizacion, Carga, Pedido, SolicitudPedido
from src.core.personnel.models import Personal
from src.core.personnel_types.models import PersonnelType
from src.core.sectors.models import Sector
from src.core.users.models import User

FECHA = date(2026, 10, 13)
OTRA_FECHA = date(2026, 10, 14)
# created_at se guarda en UTC: el 13/10 a las 12:00 en Argentina son las 15:00 UTC.
MEDIODIA_UTC = datetime(2026, 10, 13, 15, 0)
# Una cena del 13/10 a las 22:00 en Argentina queda guardada el 14/10 a la 01:00 UTC.
CENA_22_UTC = datetime(2026, 10, 14, 1, 0)


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
    """Crea sectores, comidas, dos menús, un usuario del Comedor y dos personas."""
    guardia = Sector(nombre="Guardia", activo=True)
    pediatria = Sector(nombre="Pediatría", activo=True)
    clinica = Sector(nombre="Clínica", activo=True)
    rol = Role(name="Sector Comedor")
    tipo_personal = PersonnelType(nombre="Personal Fijo")
    vegetariano = MenuType(nombre="Vegetariano")
    general = MenuType(nombre="General")
    almuerzo = FoodType(nombre="Almuerzo")
    cena = FoodType(nombre="Cena")
    db.session.add_all([
        guardia, pediatria, clinica, rol, tipo_personal,
        vegetariano, general, almuerzo, cena,
    ])
    db.session.flush()

    usuario = User(
        email="comedor@test.com",
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
    db.session.add_all([usuario, ana, luis])
    db.session.commit()

    return {
        "guardia": guardia,
        "pediatria": pediatria,
        "clinica": clinica,
        "vegetariano": vegetariano,
        "general": general,
        "almuerzo": almuerzo,
        "cena": cena,
        "usuario": usuario,
        "ana": ana,
        "luis": luis,
    }


def autorizar(datos, persona, sector, comida, menu, fecha=FECHA):
    """Crea un pedido autorizado con una solicitud autorizada para la persona.

    Va directo con los modelos porque la API de autorizaciones hoy da 500 (issue #13).
    """
    usuario = datos["usuario"]
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


def entregar(datos, autorizaciones, comida, created_at=MEDIODIA_UTC):
    """Crea una entrega directo con los modelos, con la hora que se le pase.

    No usa registrar_entrega para poder fijar created_at sin depender del turno.
    """
    entrega = Entrega(
        usuario_id=datos["usuario"].id,
        responsable_id=datos["ana"].id,
        tipo_comida_id=comida.id,
        created_at=created_at,
        detalles=[
            EntregaDetalle(autorizacion_id=autorizacion.id)
            for autorizacion in autorizaciones
        ],
    )
    db.session.add(entrega)
    db.session.commit()
    return entrega


def test_filtra_por_fecha_del_pedido(datos):
    autorizacion = autorizar(
        datos, datos["ana"], datos["guardia"], datos["cena"], datos["vegetariano"]
    )
    cena = entregar(datos, [autorizacion], datos["cena"], created_at=CENA_22_UTC)

    assert listar_entregas(fecha=FECHA).all() == [cena]
    assert listar_entregas(fecha=OTRA_FECHA).all() == []


def test_filtra_por_sector_sin_repetir(datos):
    de_ana = autorizar(
        datos, datos["ana"], datos["guardia"], datos["almuerzo"], datos["vegetariano"]
    )
    de_luis = autorizar(
        datos, datos["luis"], datos["pediatria"], datos["almuerzo"], datos["general"]
    )
    entrega = entregar(datos, [de_ana, de_luis], datos["almuerzo"])

    assert listar_entregas().all() == [entrega]
    assert listar_entregas(sector_id=datos["guardia"].id).all() == [entrega]
    assert listar_entregas(sector_id=datos["pediatria"].id).all() == [entrega]
    assert listar_entregas(sector_id=datos["clinica"].id).all() == []
    assert listar_entregas(fecha=FECHA, sector_id=datos["guardia"].id).count() == 1


def test_filtra_por_comida(datos):
    almuerzo = entregar(
        datos,
        [autorizar(datos, datos["ana"], datos["guardia"], datos["almuerzo"], datos["vegetariano"])],
        datos["almuerzo"],
    )
    cena = entregar(
        datos,
        [autorizar(datos, datos["ana"], datos["guardia"], datos["cena"], datos["vegetariano"])],
        datos["cena"],
        created_at=CENA_22_UTC,
    )

    assert listar_entregas(tipo_comida_id=datos["almuerzo"].id).all() == [almuerzo]
    assert listar_entregas(tipo_comida_id=datos["cena"].id).all() == [cena]
    # Sin filtros, la más reciente primero.
    assert listar_entregas().all() == [cena, almuerzo]


def test_obtener_entrega(datos):
    autorizacion = autorizar(
        datos, datos["ana"], datos["guardia"], datos["almuerzo"], datos["vegetariano"]
    )
    entrega = entregar(datos, [autorizacion], datos["almuerzo"])

    assert obtener_entrega(entrega.id) == entrega


def test_obtener_entrega_inexistente(app):
    with pytest.raises(LookupError):
        obtener_entrega(9999)


def test_datos_entrega(datos):
    autorizacion = autorizar(
        datos, datos["luis"], datos["pediatria"], datos["cena"], datos["general"]
    )
    entrega = entregar(datos, [autorizacion], datos["cena"], created_at=CENA_22_UTC)

    resultado = datos_entrega(obtener_entrega(entrega.id))

    assert resultado["id"] == entrega.id
    assert resultado["fecha_hora"] == "2026-10-13T22:00:00-03:00"
    assert resultado["usuario"] == {
        "id": datos["usuario"].id,
        "email": "comedor@test.com",
    }
    assert resultado["responsable"]["dni"] == "30000001"
    assert resultado["tipo_comida"]["nombre"] == "Cena"
    assert resultado["personas"] == [{
        "id": datos["luis"].id,
        "dni": "30000002",
        "nombre": "Luis",
        "apellido": "Pérez",
        "tipo_menu": {"id": datos["general"].id, "nombre": "General"},
        "condicion": "regular",
        "sector": {"id": datos["pediatria"].id, "nombre": "Pediatría"},
    }]


def test_resumen_por_comida_y_menu(datos):
    almuerzo_ana = autorizar(
        datos, datos["ana"], datos["guardia"], datos["almuerzo"], datos["vegetariano"]
    )
    autorizar(datos, datos["luis"], datos["pediatria"], datos["almuerzo"], datos["general"])
    autorizar(datos, datos["ana"], datos["guardia"], datos["cena"], datos["vegetariano"])
    entregar(datos, [almuerzo_ana], datos["almuerzo"])

    assert resumen_entregas(fecha=FECHA) == [
        {"tipo_comida": "Almuerzo", "tipo_menu": "General",
         "autorizadas": 1, "entregadas": 0, "diferencia": 1},
        {"tipo_comida": "Almuerzo", "tipo_menu": "Vegetariano",
         "autorizadas": 1, "entregadas": 1, "diferencia": 0},
        {"tipo_comida": "Cena", "tipo_menu": "Vegetariano",
         "autorizadas": 1, "entregadas": 0, "diferencia": 1},
    ]
    assert resumen_entregas(tipo_comida_id=datos["cena"].id) == [
        {"tipo_comida": "Cena", "tipo_menu": "Vegetariano",
         "autorizadas": 1, "entregadas": 0, "diferencia": 1},
    ]
    assert resumen_entregas(fecha=OTRA_FECHA) == []


def test_resumen_dos_autorizaciones_cuenta_por_autorizacion(datos):
    ana = datos["ana"]
    de_guardia = autorizar(datos, ana, datos["guardia"], datos["almuerzo"], datos["vegetariano"])
    autorizar(datos, ana, datos["pediatria"], datos["almuerzo"], datos["vegetariano"])
    entregar(datos, [de_guardia], datos["almuerzo"])

    assert resumen_entregas(fecha=FECHA) == [
        {"tipo_comida": "Almuerzo", "tipo_menu": "Vegetariano",
         "autorizadas": 2, "entregadas": 1, "diferencia": 1},
    ]
    assert resumen_entregas(fecha=FECHA, sector_id=datos["pediatria"].id)[0]["entregadas"] == 0
