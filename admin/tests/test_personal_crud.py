import pytest
from src.web import create_app
from src.core import personnel
from src.core.personnel.models import Personal
from src.core.db import db


@pytest.fixture
def test_setup():
    app = create_app()
    client = app.test_client()
    with app.app_context():
        yield app, client


def test_listado_personal_status(test_setup):
    _, client = test_setup
    res = client.get("/personal/")
    assert res.status_code == 200
    assert "Personal del Hospital" in res.text


def test_ciclo_completo_alta_edicion_eliminacion(test_setup):
    _, client = test_setup
    dni_test = "77112233"

    p_previa = Personal.query.filter_by(dni=dni_test).first()
    if p_previa:
        db.session.delete(p_previa)
        db.session.commit()

    tipos = personnel.list_personnel_types()
    menus = personnel.list_menu_types()
    sectores = personnel.list_active_sectors()

    data_alta = {
        "dni": dni_test,
        "nombre": "Martin",
        "apellido": "Palermo",
        "personnel_type_id": str(tipos[0].id),
        "sector_id": str(sectores[0].id) if sectores else "",
        "menu_type_id": str(menus[0].id),
    }
    res_alta = client.post("/personal/nuevo", data=data_alta, follow_redirects=True)
    assert res_alta.status_code == 200

    persona = Personal.query.filter_by(dni=dni_test).first()
    assert persona is not None
    assert persona.nombre == "Martin"
    assert persona.activo is True

    data_edit = {
        "dni": dni_test,
        "nombre": "Martin Modificado",
        "apellido": "Palermo Actualizado",
        "personnel_type_id": str(tipos[0].id),
        "sector_id": str(sectores[0].id) if sectores else "",
        "menu_type_id": str(menus[0].id),
    }
    res_edit = client.post(f"/personal/{persona.id}/editar", data=data_edit, follow_redirects=True)
    assert res_edit.status_code == 200

    db.session.refresh(persona)
    assert persona.nombre == "Martin Modificado"

    persona_id = persona.id
    res_del = client.post(f"/personal/{persona_id}/eliminar", follow_redirects=True)
    assert res_del.status_code == 200

    eliminada = Personal.query.get(persona_id)
    assert eliminada is None


def test_baja_logica_cuando_posee_pedidos(test_setup):
    _, client = test_setup
    dni_test = "77445566"
    tipos = personnel.list_personnel_types()
    menus = personnel.list_menu_types()

    data = {
        "dni": dni_test,
        "nombre": "Roman",
        "apellido": "Riquelme",
        "personnel_type_id": str(tipos[0].id),
        "sector_id": "",
        "menu_type_id": str(menus[0].id),
    }
    persona = personnel.create_personnel(data)

    orig_has_order = personnel.has_order_history
    personnel.has_order_history = lambda pid: True

    try:
        client.post(f"/personal/{persona.id}/eliminar", follow_redirects=True)
        db.session.refresh(persona)
        assert persona.activo is False
    finally:
        personnel.has_order_history = orig_has_order
        db.session.delete(persona)
        db.session.commit()