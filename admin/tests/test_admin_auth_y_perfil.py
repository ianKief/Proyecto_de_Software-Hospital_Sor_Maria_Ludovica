"""Pruebas de autenticación en el panel de administración y gestión del perfil de Administrador."""
import bcrypt
import pytest

from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role, Permission
from src.core.users.models import User
from src.core.configuration.models import Configuration, ID_CONFIGURACION
from src.core.tokens import generar_token_activacion, generar_token_magic_login


def _hash_password(texto):
    return bcrypt.hashpw(texto.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app(env="testing")
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        db.session.add(Configuration(
            id=ID_CONFIGURACION,
            elementos_por_pagina=25,
            mantenimiento_activo=False,
            mensaje_mantenimiento="Sitio en mantenimiento",
        ))

        rol_admin = Role(name="Administrador")
        rol_jefe = Role(name="Jefe de Servicio")
        perm_show = Permission(name="user_show")
        perm_update = Permission(name="user_update")
        rol_admin.permissions.extend([perm_show, perm_update])

        db.session.add_all([rol_admin, rol_jefe, perm_show, perm_update])
        db.session.flush()

        admin = User(
            email="admin@hospital.com",
            nombre="Carlos",
            apellido="Admin",
            dni="11223344",
            password=_hash_password("admin123"),
            activo=True,
            role_id=rol_admin.id,
        )
        jefe = User(
            email="jefe@hospital.com",
            nombre="Laura",
            apellido="Jefa",
            dni="22334455",
            password=_hash_password("jefe123"),
            activo=True,
            role_id=rol_jefe.id,
        )
        jefe_pendiente = User(
            email="nuevo_jefe@hospital.com",
            nombre="Pedro",
            apellido="Nuevo",
            dni="33445566",
            password=_hash_password("temporal"),
            activo=False,
            role_id=rol_jefe.id,
        )
        db.session.add_all([admin, jefe, jefe_pendiente])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def test_login_admin_permite_ingreso_a_administrador(app):
    client = app.test_client()
    resp = client.post("/auth/login", data={
        "email": "admin@hospital.com",
        "password": "admin123",
    }, follow_redirects=True)

    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("user") == "admin@hospital.com"
        assert sess.get("role") == "Administrador"


def test_login_admin_rechaza_roles_operativos(app):
    client = app.test_client()
    resp = client.post("/auth/login", data={
        "email": "jefe@hospital.com",
        "password": "jefe123",
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert "exclusivo para usuarios con rol Administrador" in resp.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert sess.get("user") is None


def test_magic_login_rechaza_roles_operativos(app):
    client = app.test_client()
    jefe = User.query.filter_by(email="jefe@hospital.com").first()
    token = generar_token_magic_login(jefe.id)

    resp = client.get(f"/auth/magic-login?token={token}", follow_redirects=True)
    assert resp.status_code == 200
    assert "exclusivo para usuarios con rol Administrador" in resp.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert sess.get("user") is None


def test_set_password_activa_rol_operativo_sin_iniciar_sesion_en_admin(app):
    client = app.test_client()
    jefe_nuevo = User.query.filter_by(email="nuevo_jefe@hospital.com").first()
    token = generar_token_activacion(jefe_nuevo.id)

    resp = client.post("/auth/set-password", data={
        "token": token,
        "password": "nuevaclave123",
        "password_confirm": "nuevaclave123",
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert "portal" in resp.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert sess.get("user") is None

    jefe_actualizado = User.query.filter_by(email="nuevo_jefe@hospital.com").first()
    assert jefe_actualizado.activo is True
    assert bcrypt.checkpw(b"nuevaclave123", jefe_actualizado.password.encode("utf-8"))


def test_perfil_accesible_y_editable_solo_por_administrador(app):
    client = app.test_client()

    admin = User.query.filter_by(email="admin@hospital.com").first()
    jefe = User.query.filter_by(email="jefe@hospital.com").first()
    admin_id = admin.id
    jefe_id = jefe.id

    # Si un rol operativo tuviese sesión, recibe 403 al intentar ver o editar perfil en admin
    with client.session_transaction() as sess:
        sess["user"] = "jefe@hospital.com"
        sess["user_id"] = jefe_id
        sess["role"] = "Jefe de Servicio"

    assert client.get("/users/perfil").status_code == 403
    assert client.get("/users/perfil/editar").status_code == 403

    # El Administrador sí puede ver y actualizar su propio perfil y contraseña
    with client.session_transaction() as sess:
        sess["user"] = "admin@hospital.com"
        sess["user_id"] = admin_id
        sess["role"] = "Administrador"

    resp_show = client.get("/users/perfil")
    assert resp_show.status_code == 200
    assert "Carlos Admin" in resp_show.get_data(as_text=True)

    resp_edit = client.post("/users/perfil/editar", data={
        "nombre": "Carlos Alberto",
        "apellido": "Admin",
        "email": "admin@hospital.com",
        "dni": "11223344",
        "password": "nueva_admin_123",
        "password_confirm": "nueva_admin_123",
    }, follow_redirects=True)
    assert resp_edit.status_code == 200
    assert "Perfil actualizado con éxito" in resp_edit.get_data(as_text=True)

    admin_db = db.session.get(User, admin_id)
    assert admin_db.nombre == "Carlos Alberto"
    assert bcrypt.checkpw(b"nueva_admin_123", admin_db.password.encode("utf-8"))
