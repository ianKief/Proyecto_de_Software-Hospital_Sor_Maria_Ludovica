import pytest
from src.web import create_app
from src.core.quotas.models import Cupo
from src.core.sectors.models import Sector
from src.core.food_types.models import FoodType
from src.core.users.models import User
from src.core.auth.models import Role, Permission
from src.core.db import db


@pytest.fixture
def test_setup():
    app = create_app()
    client = app.test_client()
    with app.app_context():
        # Asegurar permisos y rol de prueba
        rol = Role.query.filter_by(name="Servicio de Alimentación").first()
        if not rol:
            rol = Role(name="Servicio de Alimentación")
            db.session.add(rol)
            db.session.flush()

        for p_name in ["quota_index", "quota_show", "quota_new", "quota_update", "quota_destroy"]:
            perm = Permission.query.filter_by(name=p_name).first()
            if not perm:
                perm = Permission(name=p_name)
                db.session.add(perm)
                db.session.flush()
            if perm not in rol.permissions:
                rol.permissions.append(perm)

        # Crear o buscar usuario autenticado para el test
        user = User.query.filter_by(email="test_crud_cupos@hospital.com").first()
        if not user:
            user = User(
                email="test_crud_cupos@hospital.com",
                nombre="Test",
                apellido="Cupos",
                dni="99887766",
                password="hashed_dummy_password",
                activo=True,
                role_id=rol.id,
            )
            db.session.add(user)
            db.session.commit()

        # Inyectar sesión autenticada en el cliente
        with client.session_transaction() as sess:
            sess["user"] = user.email
            sess["user_id"] = user.id

        yield app, client


def _obtener_o_crear_recursos_crud():
    sector = Sector.query.filter_by(activo=True).first()
    if not sector:
        sector = Sector(nombre="Sector CRUD Cupos", descripcion="Sector test", activo=True)
        db.session.add(sector)
        db.session.commit()

    comida = FoodType.query.first()
    if not comida:
        comida = FoodType(nombre="Cena Test")
        db.session.add(comida)
        db.session.commit()

    return sector, comida


def test_listado_cupos_responde_ok(test_setup):
    _, client = test_setup
    res = client.get("/cupos/")
    assert res.status_code == 200
    assert "Cupos por Sector" in res.text


def test_ciclo_completo_cupos(test_setup):
    _, client = test_setup
    sector, comida = _obtener_o_crear_recursos_crud()
    s_id = sector.id
    c_id = comida.id

    prev = Cupo.query.filter_by(sector_id=s_id, tipo_comida_id=c_id).first()
    if prev:
        db.session.delete(prev)
        db.session.commit()

    # 1. ALTA
    data_alta = {
        "sector_id": str(s_id),
        "tipo_comida_id": str(c_id),
        "cantidad": "25",
    }
    res_alta = client.post("/cupos/nuevo", data=data_alta, follow_redirects=True)
    assert res_alta.status_code == 200

    cupo = Cupo.query.filter_by(sector_id=s_id, tipo_comida_id=c_id).first()
    assert cupo is not None
    assert cupo.cantidad == 25

    # 2. EDICIÓN
    data_edit = {
        "sector_id": str(s_id),
        "tipo_comida_id": str(c_id),
        "cantidad": "40",
    }
    res_edit = client.post(f"/cupos/{cupo.id}/editar", data=data_edit, follow_redirects=True)
    assert res_edit.status_code == 200

    db.session.refresh(cupo)
    assert cupo.cantidad == 40

    # 3. ELIMINACIÓN
    cupo_id = cupo.id
    res_del = client.post(f"/cupos/{cupo_id}/eliminar", follow_redirects=True)
    assert res_del.status_code == 200

    cupo_borrado = Cupo.query.get(cupo_id)
    assert cupo_borrado is None