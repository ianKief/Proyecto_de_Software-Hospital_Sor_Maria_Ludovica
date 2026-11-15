
from datetime import date
from types import SimpleNamespace

from src.web.controllers import pedidos as pedidos_controller
from src.web.helpers import api_auth


def preparar_cliente(monkeypatch, app):
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    client = app.test_client()

    permisos = [
        SimpleNamespace(name="request_update"),
        SimpleNamespace(name="request_destroy"),
    ]

    usuario = SimpleNamespace(
        id=1,
        activo=True,
        role=SimpleNamespace(permissions=permisos),
    )

    monkeypatch.setattr(
        api_auth,
        "_obtener_usuario_desde_token",
        lambda: (usuario, None),
    )

    return client


def test_modificar_pedido_correctamente(monkeypatch, app):
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

    response = preparar_cliente(monkeypatch, app).put(
        "/api/requests/3",
        json={"periodicidad": "diaria"},
    )

    assert response.status_code == 200
    assert response.json["mensaje"] == (
        "Pedido modificado correctamente"
    )
    assert response.json["pedido"]["id"] == 3
    assert response.json["pedido"]["solicitudes"][0]["person_id"] == 2


def test_modificar_pedido_en_conflicto_devuelve_409(monkeypatch, app):
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

    response = preparar_cliente(monkeypatch, app).put(
        "/api/requests/3",
        json={"periodicidad": "diaria"},
    )

    assert response.status_code == 409
    assert response.json["error"] == (
        "El pedido ya no se puede modificar"
    )


def test_eliminar_pedido_correctamente(monkeypatch, app):
    monkeypatch.setattr(
        pedidos_controller,
        "eliminar_pedido_core",
        lambda **kwargs: None,
    )

    response = preparar_cliente(monkeypatch, app).delete(
        "/api/requests/3",
    )

    assert response.status_code == 200
    assert response.json["mensaje"] == (
        "Pedido eliminado correctamente"
    )
    assert response.json["request_id"] == 3


def test_eliminar_pedido_en_conflicto_devuelve_409(monkeypatch, app):
    def eliminar_con_conflicto(**kwargs):
        raise RuntimeError("El pedido ya no se puede eliminar")

    monkeypatch.setattr(
        pedidos_controller,
        "eliminar_pedido_core",
        eliminar_con_conflicto,
    )

    response = preparar_cliente(monkeypatch, app).delete(
        "/api/requests/3",
    )

    assert response.status_code == 409
    assert response.json["error"] == (
        "El pedido ya no se puede eliminar"
    )
