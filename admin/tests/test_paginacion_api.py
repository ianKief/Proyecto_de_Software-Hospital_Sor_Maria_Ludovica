
from datetime import date
from types import SimpleNamespace

from src.web.controllers import authorizations as auth_controller
from src.web.controllers import pedidos as pedidos_controller
from src.web.helpers import api_auth


def preparar_cliente(monkeypatch, app, rol):
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    client = app.test_client()

    permisos = [
        SimpleNamespace(name="request_index"),
        SimpleNamespace(name="authorization_index"),
    ]

    usuario = SimpleNamespace(
        id=1,
        activo=True,
        sector_id=3,
        role=SimpleNamespace(
            name=rol,
            permissions=permisos,
        ),
    )

    monkeypatch.setattr(
        api_auth,
        "_obtener_usuario_desde_token",
        lambda: (usuario, None),
    )

    return client


def crear_pedido_falso():
    return SimpleNamespace(
        id=5,
        sector_id=3,
        fecha=date(2026, 10, 12),
        estado="confirmado",
        creado_por=1,
        solicitudes=[],
    )


def crear_pagina_falsa(pedido):
    return SimpleNamespace(
        items=[pedido],
        page=2,
        per_page=10,
        total=11,
        pages=2,
    )


def test_listado_pedidos_usa_respuesta_paginada(monkeypatch, app):
    pedido = crear_pedido_falso()
    pagina = crear_pagina_falsa(pedido)

    monkeypatch.setattr(
        pedidos_controller,
        "listar_pedidos_core",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        pedidos_controller,
        "paginar",
        lambda consulta, numero: pagina,
    )

    client = preparar_cliente(monkeypatch, app, "Jefe de Servicio")
    response = client.get("/api/requests?page=2")

    assert response.status_code == 200
    assert response.json["items"][0]["id"] == 5
    assert response.json["pagina"] == 2
    assert response.json["por_pagina"] == 10
    assert response.json["total"] == 11
    assert response.json["paginas"] == 2
    assert "pedidos" not in response.json


def test_listado_pedidos_rechaza_pagina_invalida(monkeypatch, app):
    client = preparar_cliente(monkeypatch, app, "Jefe de Servicio")
    response = client.get("/api/requests?page=abc")

    assert response.status_code == 400


def test_listado_autorizaciones_usa_respuesta_paginada(monkeypatch, app):
    pedido = crear_pedido_falso()
    pagina = crear_pagina_falsa(pedido)

    monkeypatch.setattr(
        auth_controller,
        "listar_autorizaciones_core",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        auth_controller,
        "paginar",
        lambda consulta, numero: pagina,
    )
    monkeypatch.setattr(
        auth_controller,
        "armar_detalle_pedido",
        lambda pedido: {"id": pedido.id},
    )

    client = preparar_cliente(
        monkeypatch,
        app,
        "Servicio de Alimentación",
    )
    response = client.get("/api/authorizations?page=2")

    assert response.status_code == 200
    assert response.json["items"] == [{"id": 5}]
    assert response.json["pagina"] == 2
    assert response.json["por_pagina"] == 10
    assert response.json["total"] == 11
    assert response.json["paginas"] == 2
    assert "pedidos" not in response.json


def test_listado_autorizaciones_rechaza_pagina_invalida(monkeypatch, app):
    client = preparar_cliente(
        monkeypatch,
        app,
        "Servicio de Alimentación",
    )
    response = client.get("/api/authorizations?page=abc")

    assert response.status_code == 400
