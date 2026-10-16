import io
import pytest
from src.web import create_app
from src.core.db import db
from src.core.personnel.models import Personnel
from src.core.personnel_types.models import PersonnelType
from src.core.menu_types.models import MenuType
from src.core.sectors.models import Sector
from src.core.users.models import User
from src.core.auth.models import Role, Permission


@pytest.fixture
def test_setup():
    app = create_app()
    client = app.test_client()
    with app.app_context():
        rol = Role.query.filter_by(name="Administrador").first()
        if not rol:
            rol = Role(name="Administrador")
            db.session.add(rol)
            db.session.flush()

        p_import = Permission.query.filter_by(name="personnel_import").first()
        if not p_import:
            p_import = Permission(name="personnel_import")
            db.session.add(p_import)
            db.session.flush()
        if p_import not in rol.permissions:
            rol.permissions.append(p_import)

        user = User.query.filter_by(email="admin_csv_test@hospital.com").first()
        if not user:
            user = User(
                email="admin_csv_test@hospital.com",
                nombre="Admin",
                apellido="CSV",
                dni="12398745",
                password="hashed_pwd",
                activo=True,
                role_id=rol.id,
            )
            db.session.add(user)
            db.session.commit()

        with client.session_transaction() as sess:
            sess["user"] = user.email
            sess["user_id"] = user.id

        yield app, client


def test_importacion_exitosa(test_setup):
    _, client = test_setup

    tp = PersonnelType.query.first() or PersonnelType(nombre="Planta Permanente", requiere_sector=True)
    tm = MenuType.query.first() or MenuType(nombre="General")
    sec = Sector.query.filter_by(activo=True).first() or Sector(nombre="Guardia General", activo=True)
    db.session.add_all([tp, tm, sec])
    db.session.commit()

    # Limpiar posibles registros previos
    Personnel.query.filter(Personnel.dni.in_(["99111222", "99111223"])).delete()
    db.session.commit()

    csv_data = (
        "dni,nombre,apellido,tipo_personal,tipo_menu,sector\n"
        f"99111222,Mariano,Lopez,{tp.nombre},{tm.nombre},{sec.nombre}\n"
        f"99111223,Sofia,Diaz,{tp.nombre},{tm.nombre},{sec.nombre}\n"
    )

    data = {
        "archivo_csv": (io.BytesIO(csv_data.encode("utf-8")), "personal.csv")
    }

    res = client.post("/personal/importar", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert res.status_code == 200
    assert "Se importaron exitosamente 2 registros" in res.text

    p1 = Personnel.query.filter_by(dni="99111222").first()
    p2 = Personnel.query.filter_by(dni="99111223").first()
    assert p1 is not None and p1.nombre == "Mariano"
    assert p2 is not None and p2.nombre == "Sofia"


def test_importacion_reporta_errores_especificos(test_setup):
    _, client = test_setup

    tp = PersonnelType.query.first()
    tm = MenuType.query.first()
    sec = Sector.query.filter_by(activo=True).first()

    csv_data = (
        "dni,nombre,apellido,tipo_personal,tipo_menu,sector\n"
        f"invalido123,Mariano,Lopez,{tp.nombre},{tm.nombre},{sec.nombre}\n"
        f"99444555,Mariano,Lopez,TipoInexistenteXYZ,{tm.nombre},{sec.nombre}\n"
    )

    data = {
        "archivo_csv": (io.BytesIO(csv_data.encode("utf-8")), "errores.csv")
    }

    res = client.post("/personal/importar", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert res.status_code == 200
    assert "Se rechazaron 2 registros" in res.text
    assert "DNI debe contener entre 7 y 9 números" in res.text
    assert "TipoInexistenteXYZ" in res.text