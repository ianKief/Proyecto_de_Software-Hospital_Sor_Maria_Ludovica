import pytest
from src.web import create_app
from src.core.personnel.models import Personal
from src.core.personnel_types.models import PersonnelType
from src.core.menu_types.models import MenuType
from src.core.sectors.models import Sector
from src.core.users.models import User
from src.core.auth.models import Role, Permission
from src.core.db import db


@pytest.fixture
def test_setup():
    app = create_app()
    client = app.test_client()
    with app.app_context():
        rol = Role.query.filter_by(name="Servicio de Alimentación").first()
        if not rol:
            rol = Role(name="Servicio de Alimentación")
            db.session.add(rol)
            db.session.flush()

        for p_name in ["personnel_index", "personnel_show", "personnel_new", "personnel_update", "personnel_destroy"]:
            perm = Permission.query.filter_by(name=p_name).first()
            if not perm:
                perm = Permission(name=p_name)
                db.session.add(perm)
                db.session.flush()
            if perm not in rol.permissions:
                rol.permissions.append(perm)

        user = User.query.filter_by(email="test_crud_personal@hospital.com").first()
        if not user:
            user = User(
                email="test_crud_personal@hospital.com",
                nombre="Test",
                apellido="Personal",
                dni="88776655",
                password="hashed_dummy_password",
                activo=True,
                role_id=rol.id,
            )
            db.session.add(user)
            db.session.commit()

        with client.session_transaction() as sess:
            sess["user"] = user.email
            sess["user_id"] = user.id

        yield app, client


def _obtener_o_crear_recursos_personal():
    tipo_p = PersonnelType.query.first()
    if not tipo_p:
        tipo_p = PersonnelType(nombre="Planta Test")
        db.session.add(tipo_p)
        db.session.commit()

    tipo_m = MenuType.query.first()
    if not tipo_m:
        tipo_m = MenuType(nombre="General Test")
        db.session.add(tipo_m)
        db.session.commit()

    sector = Sector.query.filter_by(activo=True).first()
    if not sector:
        sector = Sector(nombre="Sector Test Personal", descripcion="Sector test", activo=True)
        db.session.add(sector)
        db.session.commit()

    return tipo_p, tipo_m, sector


def test_listado_personal_responde_ok(test_setup):
    _, client = test_setup
    res = client.get("/personal/")
    assert res.status_code == 200


def test_ciclo_completo_personal(test_setup):
    _, client = test_setup
    tipo_p, tipo_m, sector = _obtener_o_crear_recursos_personal()

    dni_test = "45999888"
    prev = Personal.query.filter_by(dni=dni_test).first()
    if prev:
        db.session.delete(prev)
        db.session.commit()

    # 1. ALTA
    data_alta = {
        "dni": dni_test,
        "nombre": "Esteban",
        "apellido": "Quito",
        "personnel_type_id": str(tipo_p.id),
        "menu_type_id": str(tipo_m.id),
        "sector_id": str(sector.id),
        "activo": "true",
    }
    res_alta = client.post("/personal/nuevo", data=data_alta, follow_redirects=True)
    assert res_alta.status_code == 200

    p = Personal.query.filter_by(dni=dni_test).first()
    assert p is not None
    assert p.nombre == "Esteban"

    # 2. EDICIÓN
    data_edit = {
        "dni": dni_test,
        "nombre": "Esteban Modificado",
        "apellido": "Quito",
        "personnel_type_id": str(tipo_p.id),
        "menu_type_id": str(tipo_m.id),
        "sector_id": str(sector.id),
        "activo": "true",
    }
    res_edit = client.post(f"/personal/{p.id}/editar", data=data_edit, follow_redirects=True)
    assert res_edit.status_code == 200

    db.session.refresh(p)
    assert p.nombre == "Esteban Modificado"

    # 3. ELIMINACIÓN
    p_id = p.id
    res_del = client.post(f"/personal/{p_id}/eliminar", follow_redirects=True)
    assert res_del.status_code == 200

    p_borrado = Personal.query.get(p_id)
    assert p_borrado is None or not p_borrado.activo