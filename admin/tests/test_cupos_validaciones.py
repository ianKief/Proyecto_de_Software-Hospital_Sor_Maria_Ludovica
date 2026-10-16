import pytest
from src.web import create_app
from src.core.quotas.validators import ValidationError, validate_quota_data
from src.core.quotas.models import Cupo
from src.core.sectors.models import Sector
from src.core.food_types.models import FoodType
from src.core.db import db


@pytest.fixture
def test_setup():
    app = create_app()
    client = app.test_client()
    with app.app_context():
        yield app, client


def _obtener_o_crear_recursos():
    sector = Sector.query.filter_by(activo=True).first()
    if not sector:
        sector = Sector(nombre="Sector Test Activo", descripcion="Sector para tests", activo=True)
        db.session.add(sector)
        db.session.commit()

    comida = FoodType.query.first()
    if not comida:
        comida = FoodType(nombre="Almuerzo Test")
        db.session.add(comida)
        db.session.commit()

    return sector, comida


def test_cantidad_debe_ser_positiva(test_setup):
    sector, comida = _obtener_o_crear_recursos()

    data_cero = {
        "sector_id": str(sector.id),
        "tipo_comida_id": str(comida.id),
        "cantidad": "0",
    }
    with pytest.raises(ValidationError, match="estrictamente mayor que cero"):
        validate_quota_data(data_cero)

    data_negativa = {
        "sector_id": str(sector.id),
        "tipo_comida_id": str(comida.id),
        "cantidad": "-5",
    }
    with pytest.raises(ValidationError, match="estrictamente mayor que cero"):
        validate_quota_data(data_negativa)


def test_sector_inactivo_no_permite_cupo(test_setup):
    _, comida = _obtener_o_crear_recursos()

    sector_inactivo = Sector.query.filter_by(activo=False).first()
    creado = False
    if not sector_inactivo:
        sector_inactivo = Sector(nombre="Sector Inactivo Cupos", descripcion="Inactivo test", activo=False)
        db.session.add(sector_inactivo)
        db.session.commit()
        creado = True

    try:
        data = {
            "sector_id": str(sector_inactivo.id),
            "tipo_comida_id": str(comida.id),
            "cantidad": "10",
        }
        with pytest.raises(ValidationError, match="sector inactivo"):
            validate_quota_data(data)
    finally:
        if creado:
            db.session.delete(sector_inactivo)
            db.session.commit()


def test_no_permite_duplicar_sector_y_tipo_comida(test_setup):
    sector, comida = _obtener_o_crear_recursos()
    s_id = sector.id
    c_id = comida.id

    prev = Cupo.query.filter_by(sector_id=s_id, tipo_comida_id=c_id).first()
    if prev:
        db.session.delete(prev)
        db.session.commit()

    cupo_creado = Cupo(sector_id=s_id, tipo_comida_id=c_id, cantidad=15)
    db.session.add(cupo_creado)
    db.session.commit()

    try:
        data_duplicada = {
            "sector_id": str(s_id),
            "tipo_comida_id": str(c_id),
            "cantidad": "20",
        }
        with pytest.raises(ValidationError, match="Ya existe un cupo definido"):
            validate_quota_data(data_duplicada)

        assert validate_quota_data(data_duplicada, current_quota_id=cupo_creado.id)["cantidad"] == 20
    finally:
        db.session.delete(cupo_creado)
        db.session.commit()