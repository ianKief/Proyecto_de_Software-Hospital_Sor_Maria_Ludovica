
from types import SimpleNamespace

from src.web.controllers import authorizations as controller
from src.web.helpers import api_auth


def preparar_cliente(monkeypatch, app):
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    client = app.test_client()

    permisos = [
        SimpleNamespace(name="authorization_index"),
        SimpleNamespace(name="authorization_show"),
        SimpleNamespace(name="authorization_update"),
    ]

    usuario = SimpleNamespace(
        id=9,
        activo=True,
        role=SimpleNamespace(permissions=permisos),
    )

    monkeypatch.setattr(
        api_auth,
        "_obtener_usuario_desde_token",
        lambda: (usuario, None),
    )

    return client


def test_rechazar_pedido_correctamente(monkeypatch, app):
    pedido = SimpleNamespace(id=3)

    monkeypatch.setattr(
        controller,
        "rechazar_pedido_core",
        lambda **kwargs: pedido,
    )

    response = preparar_cliente(monkeypatch, app).post(
        "/api/authorizations/3/reject",
    )

    assert response.status_code == 200
    assert response.json["mensaje"] == (
        "Pedido rechazado correctamente"
    )
    assert response.json["request_id"] == 3
    assert response.json["usuario_id"] == 9


def test_rechazar_pedido_ya_autorizado_devuelve_409(monkeypatch, app):
    def rechazar_con_conflicto(**kwargs):
        raise RuntimeError("El pedido ya fue autorizado")

    monkeypatch.setattr(
        controller,
        "rechazar_pedido_core",
        rechazar_con_conflicto,
    )

    response = preparar_cliente(monkeypatch, app).post(
        "/api/authorizations/3/reject",
    )

    assert response.status_code == 409
    assert response.json["error"] == (
        "El pedido ya fue autorizado"
    )


def test_rechazar_pedido_inexistente_devuelve_404(monkeypatch, app):
    def rechazar_inexistente(**kwargs):
        raise LookupError("Pedido no encontrado")

    monkeypatch.setattr(
        controller,
        "rechazar_pedido_core",
        rechazar_inexistente,
    )

    response = preparar_cliente(monkeypatch, app).post(
        "/api/authorizations/999/reject",
    )

    assert response.status_code == 404
    assert response.json["error"] == "Pedido no encontrado"


def test_autorizar_pedido_correctamente(monkeypatch, app):
    pedido = SimpleNamespace(id=3, estado="autorizado")

    monkeypatch.setattr(
        controller,
        "autorizar_pedido_core",
        lambda **kwargs: pedido,
    )
    monkeypatch.setattr(
        controller,
        "armar_detalle_pedido",
        lambda pedido: {"id": pedido.id, "estado": pedido.estado},
    )

    response = preparar_cliente(monkeypatch, app).put(
        "/api/authorizations/3",
        json={
            "solicitudes": [
                {"solicitud_id": 7, "autorizada": True}
            ]
        },
    )

    assert response.status_code == 200
    assert response.json["mensaje"] == (
        "Pedido autorizado correctamente"
    )
    assert response.json["pedido"]["id"] == 3


def test_autorizar_sin_lista_de_solicitudes_devuelve_400(
    monkeypatch, app
):
    response = preparar_cliente(monkeypatch, app).put(
        "/api/authorizations/3",
        json={},
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "Debe indicar la lista de solicitudes a autorizar"
    )


def test_autorizar_pedido_inexistente_devuelve_404(monkeypatch, app):
    def autorizar_inexistente(**kwargs):
        raise LookupError("Pedido no encontrado")

    monkeypatch.setattr(
        controller,
        "autorizar_pedido_core",
        autorizar_inexistente,
    )

    response = preparar_cliente(monkeypatch, app).put(
        "/api/authorizations/999",
        json={
            "solicitudes": [
                {"solicitud_id": 7, "autorizada": True}
            ]
        },
    )

    assert response.status_code == 404
    assert response.json["error"] == "Pedido no encontrado"


def test_autorizar_pedido_procesado_devuelve_409(monkeypatch, app):
    def autorizar_con_conflicto(**kwargs):
        raise RuntimeError(
            "El pedido ya fue autorizado o rechazado"
        )

    monkeypatch.setattr(
        controller,
        "autorizar_pedido_core",
        autorizar_con_conflicto,
    )

    response = preparar_cliente(monkeypatch, app).put(
        "/api/authorizations/3",
        json={
            "solicitudes": [
                {"solicitud_id": 7, "autorizada": True}
            ]
        },
    )

    assert response.status_code == 409
    assert response.json["error"] == (
        "El pedido ya fue autorizado o rechazado"
    )


def test_autorizar_solicitud_invalida_devuelve_400(monkeypatch, app):
    def autorizar_solicitud_invalida(**kwargs):
        raise ValueError("La solicitud no pertenece al pedido")

    monkeypatch.setattr(
        controller,
        "autorizar_pedido_core",
        autorizar_solicitud_invalida,
    )

    response = preparar_cliente(monkeypatch, app).put(
        "/api/authorizations/3",
        json={
            "solicitudes": [
                {"solicitud_id": 999, "autorizada": True}
            ]
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "La solicitud no pertenece al pedido"
    )
