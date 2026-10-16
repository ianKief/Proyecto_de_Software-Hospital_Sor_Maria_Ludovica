"""Tests de los errores HTTP en la API (issue #5).

En ``/api/...`` los errores 404, 405 y 500 tienen que responder JSON
``{"error": "..."}``; en la web siguen mostrando la página HTML.
"""
import pytest

from src.web import create_app
from src.core.db import db
from src.core.configuration.models import ID_CONFIGURACION, Configuration

URL_ERROR_500 = "/api/test-error-500"
DETALLE_SECRETO = "detalle secreto"


@pytest.fixture
def app(monkeypatch):
    """App con base en memoria, la fila de configuración y una ruta que falla.

    La fila de configuración hace falta porque ``verificar_mantenimiento``
    corre antes de cada pedido, también en los que terminan en 404.
    ``PROPAGATE_EXCEPTIONS=False`` hace que la excepción llegue al handler
    de 500 en vez de cortar el test.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)

    @app.route(URL_ERROR_500)
    def ruta_que_falla():
        """Lanza una excepción para provocar un 500."""
        raise RuntimeError(DETALLE_SECRETO)

    with app.app_context():
        db.create_all()
        db.session.add(Configuration(
            id=ID_CONFIGURACION,
            elementos_por_pagina=10,
            mantenimiento_activo=False,
        ))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


def test_api_ruta_inexistente_responde_404_json(app):
    """Una ruta de la API que no existe responde 404 en JSON."""
    respuesta = app.test_client().get("/api/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.is_json
    assert respuesta.get_json() == {"error": "Recurso no encontrado"}


def test_api_metodo_no_permitido_responde_405_json(app):
    """GET a una ruta de la API que solo acepta POST responde 405 en JSON."""
    respuesta = app.test_client().get("/api/auth/login")

    assert respuesta.status_code == 405
    assert respuesta.is_json
    assert respuesta.get_json() == {"error": "Método no permitido"}


def test_api_error_interno_responde_500_json_sin_detalle(app):
    """Una excepción en la API responde 500 en JSON sin el detalle."""
    respuesta = app.test_client().get(URL_ERROR_500)

    assert respuesta.status_code == 500
    assert respuesta.is_json
    assert respuesta.get_json() == {"error": "Error interno del servidor"}
    assert DETALLE_SECRETO not in respuesta.get_data(as_text=True)


def test_web_ruta_inexistente_sigue_respondiendo_html(app):
    """Fuera de la API, el 404 sigue siendo la página HTML."""
    respuesta = app.test_client().get("/no-existe")

    assert respuesta.status_code == 404
    assert not respuesta.is_json
    assert respuesta.content_type.startswith("text/html")
