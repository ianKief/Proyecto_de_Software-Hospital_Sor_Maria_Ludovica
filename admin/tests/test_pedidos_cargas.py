from datetime import date

import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.personnel.models import Personal
from src.core.personnel_types.models import PersonnelType
from src.core.pedidos import crear_pedidos
from src.core.pedidos.models import Carga, Pedido
from src.core.sectors.models import Sector
from src.core.users.models import User


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def preparar_datos():
    sector = Sector(
        nombre="Sector de prueba",
        descripcion="Sector para tests",
        activo=True,
    )
    rol = Role(name="Jefe de Servicio")
    tipo_personal = PersonnelType(nombre="Personal Fijo")
    menu = MenuType(nombre="General")
    comida = FoodType(nombre="Desayuno")

    db.session.add_all([
        sector,
        rol,
        tipo_personal,
        menu,
        comida,
    ])
    db.session.flush()

    usuario = User(
        email="jefe@test.com",
        nombre="Jefe",
        apellido="Prueba",
        dni="10000001",
        password="hash-de-prueba",
        activo=True,
        role_id=rol.id,
        sector_id=sector.id,
    )

    persona = Personal(
        dni="10000002",
        nombre="Ana",
        apellido="Prueba",
        personnel_type_id=tipo_personal.id,
        sector_id=sector.id,
        menu_type_id=menu.id,
        activo=True,
    )

    db.session.add_all([usuario, persona])
    db.session.flush()

    carga_existente = Carga(
        creado_por=usuario.id,
        periodicidad="diaria",
        fecha_desde=date(2026, 10, 12),
        fecha_hasta=date(2026, 10, 12),
    )
    db.session.add(carga_existente)
    db.session.flush()

    pedido_existente = Pedido(
        carga_id=carga_existente.id,
        sector_id=sector.id,
        fecha=date(2026, 10, 12),
        tipo_comida_id=comida.id,
        estado="confirmado",
        creado_por=usuario.id,
    )

    db.session.add(pedido_existente)
    db.session.commit()

    return usuario, persona


def resultado_carga(fecha_desde, fecha_hasta, persona_id):
    return {
        "periodicidad": "semanal",
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "detalle": {
            "desayuno": [persona_id],
            "almuerzo": [],
            "merienda": [],
            "cena": [],
        },
    }


def test_carga_parcial_crea_pedidos_y_registra_conflicto(app):
    with app.app_context():
        usuario, persona = preparar_datos()

        pedidos, conflictos = crear_pedidos(
            usuario,
            resultado_carga(
                date(2026, 10, 12),
                date(2026, 10, 14),
                persona.id,
            ),
        )

        # El día 12 ya tiene pedido; se crean los días 13 y 14.
        assert len(pedidos) == 2

        assert [pedido.fecha for pedido in pedidos] == [
            date(2026, 10, 13),
            date(2026, 10, 14),
        ]

        assert len(conflictos) == 1
        assert conflictos[0]["fecha"] == "2026-10-12"
        assert conflictos[0]["tipo_comida"] == "Desayuno"

        # Los dos pedidos nuevos pertenecen a la misma carga.
        assert len({pedido.carga_id for pedido in pedidos}) == 1

        carga = db.session.get(Carga, pedidos[0].carga_id)

        assert carga.periodicidad == "semanal"
        assert carga.fecha_desde == date(2026, 10, 12)
        assert carga.fecha_hasta == date(2026, 10, 14)


def test_si_todas_las_fechas_chocan_no_guarda_carga_vacia(app):
    with app.app_context():
        usuario, persona = preparar_datos()
        cargas_antes = Carga.query.count()

        pedidos, conflictos = crear_pedidos(
            usuario,
            resultado_carga(
                date(2026, 10, 12),
                date(2026, 10, 12),
                persona.id,
            ),
        )

        assert pedidos == []
        assert len(conflictos) == 1
        assert conflictos[0]["fecha"] == "2026-10-12"

        # No debe quedar guardada una carga sin pedidos.
        assert Carga.query.count() == cargas_antes