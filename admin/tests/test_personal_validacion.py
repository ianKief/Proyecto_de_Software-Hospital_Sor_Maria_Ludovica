import pytest
from src.web import create_app
from src.core import personnel
from src.core.personnel.validators import ValidationError, validate_dni, validate_personnel_data
from src.core.personnel.models import Personal
from src.core.db import db


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_validate_dni_formato_correcto(app_ctx):
    assert validate_dni("1234567") == "1234567"
    assert validate_dni("40123456") == "40123456"
    assert validate_dni("123456789") == "123456789"


def test_validate_dni_formato_invalido(app_ctx):
    with pytest.raises(ValidationError, match="entre 7 y 9 números"):
        validate_dni("123456")
    with pytest.raises(ValidationError, match="entre 7 y 9 números"):
        validate_dni("1234567890")
    with pytest.raises(ValidationError, match="entre 7 y 9 números"):
        validate_dni("40.123.456")
    with pytest.raises(ValidationError, match="entre 7 y 9 números"):
        validate_dni("40123A56")
    with pytest.raises(ValidationError, match="es obligatorio"):
        validate_dni("")


def test_validate_dni_duplicado(app_ctx):
    p_existente = Personal.query.filter_by(dni="88888888").first()
    if p_existente:
        db.session.delete(p_existente)
        db.session.commit()

    tipos = personnel.list_personnel_types()
    menus = personnel.list_menu_types()
    sectores = personnel.list_active_sectors()

    persona = Personal(
        dni="88888888",
        nombre="Juan",
        apellido="Perez",
        personnel_type_id=tipos[0].id,
        sector_id=sectores[0].id if sectores else None,
        menu_type_id=menus[0].id,
        activo=True,
    )
    db.session.add(persona)
    db.session.commit()

    try:
        with pytest.raises(ValidationError, match="Ya existe una persona registrada"):
            validate_dni("88888888")
        assert validate_dni("88888888", current_personnel_id=persona.id) == "88888888"
    finally:
        db.session.delete(persona)
        db.session.commit()


def test_sector_obligatorio_para_personal_fijo(app_ctx):
    tipos = personnel.list_personnel_types()
    tipo_fijo = next((t for t in tipos if t.requiere_sector), None)

    if tipo_fijo:
        menus = personnel.list_menu_types()
        data = {
            "dni": "55667788",
            "nombre": "Esteban",
            "apellido": "Quito",
            "personnel_type_id": str(tipo_fijo.id),
            "sector_id": "",
            "menu_type_id": str(menus[0].id),
        }
        with pytest.raises(ValidationError, match="requiere un sector obligatorio"):
            validate_personnel_data(data)