from datetime import date
from types import SimpleNamespace

from src.web import create_app
from src.web.controllers import pedidos as pedidos_controller
from src.web.helpers import api_auth


def preparar_cliente(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    client = app.test_client()

    monkeypatch.setattr(
        api_auth,
        "check_permission",
        lambda permission_name: True,
    )

    monkeypatch.setattr(
        pedidos_controller,
        "_obtener_usuario_autenticado",
        lambda: SimpleNamespace(activo=True),
    )

    with client.session_transaction() as session:
        session["user"] = "jefe@hospital.com"
        session["user_id"] = 1
        session["role"] = "Jefe de Servicio"

    return client


def test_modificar_pedido_correctamente(monkeypatch):
    pedido = SimpleNamespace(
        id=3,
        sector_id=1,
        fecha=date(2026, 10, 16),
        estado="confirmado",
        creado_por=1,
        solicitudes=[
            SimpleNamespace(
                id=7,
                person_id=2,
                tipo_comida_id=1,
                tipo_menu_id=3,
                condicion="excepcion",
            )
        ],
    )

    monkeypatch.setattr(
        pedidos_controller,
        "validar_pedido",
        lambda data: (True, {"periodicidad": "diaria"}),
    )
    monkeypatch.setattr(
        pedidos_controller,
        "modificar_pedido_core",
        lambda **kwargs: pedido,
    )

    response = preparar_cliente(monkeypatch).put(
        "/api/requests/3",
        json={"periodicidad": "diaria"},
    )

    assert response.status_code == 200
    assert response.json["mensaje"] == (
        "Pedido modificado correctamente"
    )
    assert response.json["pedido"]["id"] == 3
    assert response.json["pedido"]["solicitudes"][0]["person_id"] == 2


def test_modificar_pedido_en_conflicto_devuelve_409(monkeypatch):
    monkeypatch.setattr(
        pedidos_controller,
        "validar_pedido",
        lambda data: (True, {"periodicidad": "diaria"}),
    )

    def modificar_con_conflicto(**kwargs):
        raise RuntimeError("El pedido ya no se puede modificar")

    monkeypatch.setattr(
        pedidos_controller,
        "modificar_pedido_core",
        modificar_con_conflicto,
    )

    response = preparar_cliente(monkeypatch).put(
        "/api/requests/3",
        json={"periodicidad": "diaria"},
    )

    assert response.status_code == 409
    assert response.json["error"] == (
        "El pedido ya no se puede modificar"
    )


def test_eliminar_pedido_correctamente(monkeypatch):
    monkeypatch.setattr(
        pedidos_controller,
        "eliminar_pedido_core",
        lambda **kwargs: None,
    )

    response = preparar_cliente(monkeypatch).delete(
        "/api/requests/3",
    )

    assert response.status_code == 200
    assert response.json["mensaje"] == (
        "Pedido eliminado correctamente"
    )
    assert response.json["request_id"] == 3


def test_eliminar_pedido_en_conflicto_devuelve_409(monkeypatch):
    def eliminar_con_conflicto(**kwargs):
        raise RuntimeError("El pedido ya no se puede eliminar")

    monkeypatch.setattr(
        pedidos_controller,
        "eliminar_pedido_core",
        eliminar_con_conflicto,
    )

    response = preparar_cliente(monkeypatch).delete(
        "/api/requests/3",
    )

    assert response.status_code == 409
    assert response.json["error"] == (
        "El pedido ya no se puede eliminar"
    )