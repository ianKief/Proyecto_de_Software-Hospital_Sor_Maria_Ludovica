from datetime import date

import pytest

from src.web import create_app
from src.core.db import db
from src.core.menu_types.models import MenuType
from src.core.personnel.models import (
    AsignacionSector,
    Personal,
)
from src.core.personnel_types.models import PersonnelType
from src.core.personnel import cambiar_asignacion_sector
from src.core.sectors.models import Sector


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


def preparar_personal():
    sector_anterior = Sector(
        nombre="Sector A",
        descripcion="Sector anterior",
        activo=True,
    )
    sector_nuevo = Sector(
        nombre="Sector B",
        descripcion="Sector nuevo",
        activo=True,
    )
    tipo_personal = PersonnelType(nombre="Personal Fijo")
    menu = MenuType(nombre="General")

    db.session.add_all([
        sector_anterior,
        sector_nuevo,
        tipo_personal,
        menu,
    ])
    db.session.flush()

    persona = Personal(
        dni="10000001",
        nombre="Ana",
        apellido="Prueba",
        personnel_type_id=tipo_personal.id,
        sector_id=sector_anterior.id,
        menu_type_id=menu.id,
        activo=True,
    )

    db.session.add(persona)
    db.session.flush()

    asignacion = AsignacionSector(
        personal_id=persona.id,
        sector_id=sector_anterior.id,
        fecha_desde=date(2026, 10, 1),
    )

    db.session.add(asignacion)
    db.session.commit()

    return persona, sector_anterior, sector_nuevo, asignacion


def test_cambiar_sector_conserva_historial(app):
    with app.app_context():
        persona, anterior, nuevo, asignacion_anterior = (
            preparar_personal()
        )

        cambiar_asignacion_sector(
            persona.id,
            nuevo.id,
            fecha_desde=date(2026, 10, 5),
        )

        db.session.refresh(persona)
        db.session.refresh(asignacion_anterior)

        assert persona.sector_id == nuevo.id
        assert asignacion_anterior.sector_id == anterior.id
        assert asignacion_anterior.fecha_desde == date(2026, 10, 1)
        assert asignacion_anterior.fecha_hasta == date(2026, 10, 4)

        asignacion_actual = AsignacionSector.query.filter_by(
            personal_id=persona.id,
            fecha_hasta=None,
        ).one()

        assert asignacion_actual.sector_id == nuevo.id
        assert asignacion_actual.fecha_desde == date(2026, 10, 5)


def test_quitar_sector_cierra_asignacion_actual(app):
    with app.app_context():
        persona, anterior, _, asignacion_anterior = preparar_personal()

        cambiar_asignacion_sector(
            persona.id,
            None,
            fecha_desde=date(2026, 10, 5),
        )

        db.session.refresh(persona)
        db.session.refresh(asignacion_anterior)

        assert persona.sector_id is None
        assert asignacion_anterior.fecha_hasta == date(2026, 10, 4)

        asignacion_activa = AsignacionSector.query.filter_by(
            personal_id=persona.id,
            fecha_hasta=None,
        ).first()

        assert asignacion_activa is None