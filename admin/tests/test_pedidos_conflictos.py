from datetime import date
from src.web.helpers import api_auth
from src.web import create_app
from src.web.controllers import pedidos as pedidos_controller
from types import SimpleNamespace

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
        session["user"] = "jefe@hospital.com"
        session["user_id"] = 1
        session["role"] = "Jefe de Servicio"

    return client


def test_todas_las_fechas_en_conflicto_devuelven_409(monkeypatch):
    monkeypatch.setattr(
        pedidos_controller,
        "validar_pedido",
        lambda data: (True, {"periodicidad": "semanal"}),
    )
    monkeypatch.setattr(
        pedidos_controller,
        "_obtener_usuario_autenticado",
        lambda: object(),
    )
    monkeypatch.setattr(
        pedidos_controller,
        "crear_pedidos",
        lambda **kwargs: (
            [],
            [{
                "fecha": "2026-10-12",
                "tipo_comida": "Desayuno",
                "pedido_existente_id": 1,
            }],
        ),
    )

    response = preparar_cliente(monkeypatch).post(
        "/api/requests",
        json={"prueba": True},
    )

    assert response.status_code == 409
    assert response.json["conflictos"][0]["fecha"] == "2026-10-12"
    assert response.json["error"].startswith("No se creó ningún pedido")


def test_carga_parcial_devuelve_pedidos_y_conflictos(monkeypatch):
    monkeypatch.setattr(
        pedidos_controller,
        "validar_pedido",
        lambda data: (True, {"periodicidad": "semanal"}),
    )
    monkeypatch.setattr(
        pedidos_controller,
        "_obtener_usuario_autenticado",
        lambda: object(),
    )
    monkeypatch.setattr(
        pedidos_controller,
        "crear_pedidos",
        lambda **kwargs: (
            [
                SimpleNamespace(
                    id=2,
                    sector_id=1,
                    fecha=date(2026, 10, 13),
                    estado="confirmado",
                    creado_por=1,
                    solicitudes=[],
                )
            ],
            [{
                "fecha": "2026-10-12",
                "tipo_comida": "Desayuno",
                "pedido_existente_id": 1,
            }],
        ),
    )

    response = preparar_cliente(monkeypatch).post(
        "/api/requests",
        json={"prueba": True},
    )

    assert response.status_code == 201
    assert len(response.json["pedidos"]) == 1
    assert len(response.json["conflictos"]) == 1
    assert "conflictos" in response.json["mensaje"] or (
        "disponibles" in response.json["mensaje"]
    )