
import pytest

from src.core.db import db
from src.core.personnel.models import Personnel
from src.core.personnel_types.models import PersonnelType
from src.core.menu_types.models import MenuType
from src.core.sectors.models import Sector
from src.core.personnel.validators import (
    ValidationError,
    validate_dni,
    validate_personnel_data,
    validate_csv_row,
)


def crear_recursos(requiere_sector=True, sector_activo=True):
    tipo_personal = PersonnelType(
        nombre="Planta Test",
        requiere_sector=requiere_sector,
    )
    tipo_menu = MenuType(nombre="General Test")
    sector = Sector(
        nombre="Sector Test",
        descripcion="Sector para pruebas",
        activo=sector_activo,
    )

    db.session.add_all([tipo_personal, tipo_menu, sector])
    db.session.commit()

    return tipo_personal, tipo_menu, sector


def datos_personal(tipo_personal, tipo_menu, sector, **extra):
    datos = {
        "dni": "12345678",
        "nombre": "Ana",
        "apellido": "Pérez",
        "personnel_type_id": tipo_personal.id,
        "sector_id": sector.id,
        "menu_type_id": tipo_menu.id,
        "activo": True,
    }
    datos.update(extra)
    return datos


@pytest.mark.parametrize(
    "dni",
    ["", " ", "123456", "1234567890", "12.345.678", "abc12345"],
)
def test_dni_rechaza_formato_invalido(app, dni):
    with pytest.raises(ValidationError):
        validate_dni(dni)


def test_dni_normaliza_espacios(app):
    assert validate_dni(" 12345678 ") == "12345678"


def test_dni_rechaza_duplicados(app):
    tipo_personal, tipo_menu, sector = crear_recursos()

    persona = Personnel(
        dni="12345678",
        nombre="Ana",
        apellido="Pérez",
        personnel_type_id=tipo_personal.id,
        sector_id=sector.id,
        menu_type_id=tipo_menu.id,
    )
    db.session.add(persona)
    db.session.commit()

    with pytest.raises(ValidationError, match="Ya existe una persona"):
        validate_dni("12345678")

    # Permite conservar el DNI al editar a la misma persona.
    assert validate_dni(
        "12345678",
        current_personnel_id=persona.id,
    ) == "12345678"


@pytest.mark.parametrize(
    ("campo", "mensaje"),
    [
        ("nombre", "El nombre es obligatorio"),
        ("apellido", "El apellido es obligatorio"),
    ],
)
def test_campos_nombre_y_apellido_son_obligatorios(
    app, campo, mensaje
):
    tipo_personal, tipo_menu, sector = crear_recursos()
    datos = datos_personal(tipo_personal, tipo_menu, sector)
    datos[campo] = "   "

    with pytest.raises(ValidationError, match=mensaje):
        validate_personnel_data(datos)


@pytest.mark.parametrize("campo", ["nombre", "apellido"])
def test_nombre_y_apellido_no_superan_100_caracteres(app, campo):
    tipo_personal, tipo_menu, sector = crear_recursos()
    datos = datos_personal(tipo_personal, tipo_menu, sector)
    datos[campo] = "A" * 101

    with pytest.raises(
        ValidationError,
        match=f"El {campo} no puede superar los 100 caracteres",
    ):
        validate_personnel_data(datos)


def test_tipo_personal_es_obligatorio(app):
    tipo_personal, tipo_menu, sector = crear_recursos()
    datos = datos_personal(
        tipo_personal,
        tipo_menu,
        sector,
        personnel_type_id=None,
    )

    with pytest.raises(ValidationError, match="Debe seleccionar un tipo de personal"):
        validate_personnel_data(datos)


def test_tipo_personal_inexistente(app):
    tipo_personal, tipo_menu, sector = crear_recursos()
    datos = datos_personal(
        tipo_personal,
        tipo_menu,
        sector,
        personnel_type_id=9999,
    )

    with pytest.raises(ValidationError, match="no existe"):
        validate_personnel_data(datos)


def test_sector_es_obligatorio_si_el_tipo_lo_requiere(app):
    tipo_personal, tipo_menu, sector = crear_recursos(
        requiere_sector=True,
    )
    datos = datos_personal(
        tipo_personal,
        tipo_menu,
        sector,
        sector_id=None,
    )

    with pytest.raises(ValidationError, match="requiere un sector obligatorio"):
        validate_personnel_data(datos)


def test_sector_inactivo_no_puede_asignarse(app):
    tipo_personal, tipo_menu, sector = crear_recursos(
        requiere_sector=True,
        sector_activo=False,
    )
    datos = datos_personal(tipo_personal, tipo_menu, sector)

    with pytest.raises(ValidationError, match="sector inactivo"):
        validate_personnel_data(datos)


def test_tipo_personal_que_no_requiere_sector(app):
    tipo_personal, tipo_menu, sector = crear_recursos(
        requiere_sector=False,
    )
    datos = datos_personal(tipo_personal, tipo_menu, sector)

    resultado = validate_personnel_data(datos)

    assert resultado["sector_id"] is None


def test_menu_predeterminado_es_obligatorio(app):
    tipo_personal, tipo_menu, sector = crear_recursos()
    datos = datos_personal(
        tipo_personal,
        tipo_menu,
        sector,
        menu_type_id=None,
    )

    with pytest.raises(ValidationError, match="tipo de menú predeterminado"):
        validate_personnel_data(datos)


def test_menu_inexistente(app):
    tipo_personal, tipo_menu, sector = crear_recursos()
    datos = datos_personal(
        tipo_personal,
        tipo_menu,
        sector,
        menu_type_id=9999,
    )

    with pytest.raises(ValidationError, match="no existe"):
        validate_personnel_data(datos)


def test_datos_personal_validos_se_normalizan(app):
    tipo_personal, tipo_menu, sector = crear_recursos()
    datos = datos_personal(
        tipo_personal,
        tipo_menu,
        sector,
        dni=" 12345678 ",
        nombre=" Ana ",
        apellido=" Pérez ",
        activo="false",
    )

    resultado = validate_personnel_data(datos)

    assert resultado == {
        "dni": "12345678",
        "nombre": "Ana",
        "apellido": "Pérez",
        "personnel_type_id": tipo_personal.id,
        "sector_id": sector.id,
        "menu_type_id": tipo_menu.id,
        "activo": False,
    }


def test_csv_rechaza_dni_duplicado_en_el_mismo_archivo(app):
    with pytest.raises(ValidationError, match="duplicado en el mismo archivo CSV"):
        validate_csv_row(
            {"dni": "12345678"},
            {"12345678"},
        )


def test_csv_valida_y_resuelve_nombres_de_recursos(app):
    tipo_personal, tipo_menu, sector = crear_recursos()

    fila = {
        "dni": "87654321",
        "nombre": "Carlos",
        "apellido": "Gómez",
        "tipo_personal": "Planta Test",
        "tipo_menu": "General Test",
        "sector": "Sector Test",
    }

    resultado = validate_csv_row(fila, set())

    assert resultado["dni"] == "87654321"
    assert resultado["nombre"] == "Carlos"
    assert resultado["personnel_type_id"] == tipo_personal.id
    assert resultado["menu_type_id"] == tipo_menu.id
    assert resultado["sector_id"] == sector.id
