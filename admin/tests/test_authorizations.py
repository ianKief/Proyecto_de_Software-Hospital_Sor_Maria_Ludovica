from types import SimpleNamespace
from src.web.helpers import api_auth
from src.web import create_app
from src.web.controllers import authorizations as controller
from src.core import authorizations as authorizations_core


def preparar_cliente(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    client = app.test_client()

    monkeypatch.setattr(
        api_auth,
        "check_permission",
        lambda permission_name: True,
    )

    with client.session_transaction() as session:
        session["user"] = "alimentacion@hospital.com"
        session["user_id"] = 1
        session["role"] = "Servicio de Alimentación"

    return client


def test_detalle_autorizacion_devuelve_200(monkeypatch):
    pedido = SimpleNamespace(id=7)

    monkeypatch.setattr(
        controller,
        "_obtener_pedido",
        lambda request_id: pedido,
    )
    monkeypatch.setattr(
        controller,
        "armar_detalle_pedido",
        lambda pedido: {"id": pedido.id},
    )

    response = preparar_cliente(monkeypatch).get(
        "/api/authorizations/7"
    )
    assert response.status_code == 200
    assert response.json["id"] == 7


def test_autorizar_pedido_crea_autorizacion(monkeypatch):
    app = create_app()
    pedido = SimpleNamespace(id=3, estado="confirmado")
    solicitud = SimpleNamespace(id=7, autorizacion=None)
    usuario = SimpleNamespace(id=9)

    with app.app_context():
        monkeypatch.setattr(
            authorizations_core.Pedido,
            "query",
            SimpleNamespace(get=lambda pedido_id: pedido),
        )
        monkeypatch.setattr(
            authorizations_core.SolicitudPedido,
            "query",
            SimpleNamespace(
                filter_by=lambda **kwargs: SimpleNamespace(
                    all=lambda: [solicitud]
                )
            ),
        )

        monkeypatch.setattr(
            authorizations_core.db.session,
            "flush",
            lambda: None,
        )
        monkeypatch.setattr(
            authorizations_core.db.session,
            "commit",
            lambda: None,
        )
        monkeypatch.setattr(
            authorizations_core.db.session,
            "rollback",
            lambda: None,
        )

        resultado = authorizations_core.autorizar_pedido(
            usuario,
            3,
            [{"solicitud_id": 7, "autorizada": True}],
        )

    assert resultado is pedido
    assert pedido.estado == "autorizado"
    assert solicitud.autorizacion.autorizada is True