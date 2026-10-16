"""Tests de registrar_entrega (usan una base SQLite en memoria)."""
from datetime import date, datetime, timedelta

import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role
from src.core.deliveries import registrar_entrega
from src.core.deliveries.models import Entrega, EntregaDetalle
from src.core.deliveries.turnos import ZONA_ARGENTINA, ahora, hoy
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Autorizacion, Carga, Pedido, SolicitudPedido
from src.core.personnel.models import Personal
from src.core.personnel_types.models import PersonnelType
from src.core.sectors.models import Sector
from src.core.users.models import User

FECHA = date(2026, 10, 13)
MEDIODIA = datetime(2026, 10, 13, 12, 0, tzinfo=ZONA_ARGENTINA)


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
def al_mediodia(monkeypatch):
    """Fija la hora de Entregas en el 13/10/2026 a las 12:00 (turno de Almuerzo)."""
    monkeypatch.setattr("src.core.deliveries.ahora", lambda: MEDIODIA)


@pytest.fixture
def datos(app, al_mediodia):
    """Crea sectores, comidas, menú, un usuario del Comedor y dos personas."""
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
    rol = Role(name="Sector Comedor")
    tipo_personal = PersonnelType(nombre="Personal Fijo")
    menu = MenuType(nombre="Vegetariano")
    almuerzo = FoodType(nombre="Almuerzo")
    cena = FoodType(nombre="Cena")
    db.session.add_all([guardia, pediatria, rol, tipo_personal, menu, almuerzo, cena])
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


def autorizar(datos, persona, sector, comida, fecha=FECHA):
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
    db.session.commit()
    return autorizacion


def pedido_de_entrega(datos, personas, comida=None, responsable=None):
    """Arma el diccionario que devolvería el validador de E3."""
    return {
        "personas": [persona.id for persona in personas],
        "tipo_comida_id": (comida or datos["almuerzo"]).id,
        "responsable_id": (responsable or datos["ana"]).id,
    }


def test_entrega_valida_con_dos_personas(datos):
    ana, luis = datos["ana"], datos["luis"]
    de_ana = autorizar(datos, ana, datos["guardia"], datos["almuerzo"])
    de_luis = autorizar(datos, luis, datos["pediatria"], datos["almuerzo"])

    entrega = registrar_entrega(
        pedido_de_entrega(datos, [ana, luis], responsable=luis),
        datos["usuario"].id,
    )

    assert Entrega.query.count() == 1
    assert EntregaDetalle.query.count() == 2
    assert entrega.usuario_id == datos["usuario"].id
    assert entrega.responsable_id == luis.id
    assert entrega.tipo_comida_id == datos["almuerzo"].id
    assert {d.autorizacion_id for d in entrega.detalles} == {de_ana.id, de_luis.id}
    # Las 12:00 de Argentina se guardan como las 15:00 UTC, sin zona.
    assert entrega.created_at == datetime(2026, 10, 13, 15, 0)


def test_fuera_de_horario(datos):
    autorizar(datos, datos["ana"], datos["guardia"], datos["cena"])

    with pytest.raises(ValueError, match="Fuera del horario de Cena"):
        registrar_entrega(
            pedido_de_entrega(datos, [datos["ana"]], comida=datos["cena"]),
            datos["usuario"].id,
        )

    assert Entrega.query.count() == 0


def test_comida_inexistente(datos):
    entrega = pedido_de_entrega(datos, [datos["ana"]])
    entrega["tipo_comida_id"] = 9999

    with pytest.raises(ValueError, match="tipo de comida"):
        registrar_entrega(entrega, datos["usuario"].id)


def test_responsable_inexistente(datos):
    entrega = pedido_de_entrega(datos, [datos["ana"]])
    entrega["responsable_id"] = 9999

    with pytest.raises(ValueError, match="responsable"):
        registrar_entrega(entrega, datos["usuario"].id)


def test_persona_sin_autorizacion_no_crea_nada(datos):
    ana, luis = datos["ana"], datos["luis"]
    autorizar(datos, ana, datos["guardia"], datos["almuerzo"])

    with pytest.raises(ValueError, match=f"Sin autorización.*{luis.id}"):
        registrar_entrega(pedido_de_entrega(datos, [ana, luis]), datos["usuario"].id)

    assert Entrega.query.count() == 0
    assert EntregaDetalle.query.count() == 0


def test_persona_ya_entregada_no_crea_nada(datos):
    ana, luis = datos["ana"], datos["luis"]
    autorizar(datos, ana, datos["guardia"], datos["almuerzo"])
    autorizar(datos, luis, datos["pediatria"], datos["almuerzo"])
    registrar_entrega(pedido_de_entrega(datos, [ana]), datos["usuario"].id)

    with pytest.raises(RuntimeError, match=f"Ya retiraron.*{ana.id}"):
        registrar_entrega(pedido_de_entrega(datos, [luis, ana]), datos["usuario"].id)

    assert Entrega.query.count() == 1
    assert EntregaDetalle.query.count() == 1


def test_dos_autorizaciones_usa_la_primera_y_no_entrega_dos_veces(datos):
    ana = datos["ana"]
    de_guardia = autorizar(datos, ana, datos["guardia"], datos["almuerzo"])
    autorizar(datos, ana, datos["pediatria"], datos["almuerzo"])

    entrega = registrar_entrega(pedido_de_entrega(datos, [ana]), datos["usuario"].id)

    assert [d.autorizacion_id for d in entrega.detalles] == [de_guardia.id]
    with pytest.raises(RuntimeError):
        registrar_entrega(pedido_de_entrega(datos, [ana]), datos["usuario"].id)
    assert Entrega.query.count() == 1


def test_ahora_da_hora_de_argentina():
    assert ahora().utcoffset() == timedelta(hours=-3)
    assert hoy() == ahora().date()
