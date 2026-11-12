"""Tests de pedido_editable (usan una base SQLite en memoria).

El horario de corte sale de la configuración. Como la fixture no crea la
fila, ``obtener_configuracion()`` la crea con el corte inicial (20:00).
Todos los tests usan un pedido para el 13/11/2026: su corte es el 12/11 a las 20:00.
"""
from datetime import date, datetime, time, timezone

import pytest

from src.web import create_app
from src.core.db import db
from src.core.configuration import obtener_configuracion, pedido_editable

FECHA_PEDIDO = date(2026, 11, 13)


@pytest.fixture
def app(monkeypatch):
    """App con base en memoria y todas las tablas creadas."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_antes_del_corte_se_puede(app):
    assert pedido_editable(FECHA_PEDIDO, datetime(2026, 11, 12, 19, 59)) is True


def test_dos_dias_antes_se_puede_a_cualquier_hora(app):
    assert pedido_editable(FECHA_PEDIDO, datetime(2026, 11, 11, 23, 0)) is True


def test_justo_en_el_corte_no_se_puede(app):
    assert pedido_editable(FECHA_PEDIDO, datetime(2026, 11, 12, 20, 0)) is False


def test_despues_del_corte_no_se_puede(app):
    assert pedido_editable(FECHA_PEDIDO, datetime(2026, 11, 12, 20, 1)) is False


def test_pedido_para_hoy_no_se_puede(app):
    assert pedido_editable(FECHA_PEDIDO, datetime(2026, 11, 13, 8, 0)) is False


def test_fecha_pasada_no_se_puede(app):
    assert pedido_editable(date(2026, 11, 10), datetime(2026, 11, 12, 8, 0)) is False


def test_usa_el_corte_de_la_configuracion(app):
    configuracion = obtener_configuracion()
    configuracion.horario_corte = time(18, 0)
    db.session.commit()

    assert pedido_editable(FECHA_PEDIDO, datetime(2026, 11, 12, 19, 0)) is False
    assert pedido_editable(FECHA_PEDIDO, datetime(2026, 11, 12, 17, 59)) is True


def test_hora_en_utc_se_pasa_a_hora_argentina(app):
    # 12/11 a las 23:30 UTC son las 20:30 en Argentina: ya pasó el corte.
    ahora_utc = datetime(2026, 11, 12, 23, 30, tzinfo=timezone.utc)

    assert pedido_editable(FECHA_PEDIDO, ahora_utc) is False
