"""Tests de los turnos de comida (usan una base SQLite en memoria).

Los horarios salen de la configuración. Como la fixture no crea la fila,
``obtener_configuracion()`` la crea con los valores iniciales, que son los
que prueban los primeros tests.
"""
from datetime import datetime, time

import pytest

from src.web import create_app
from src.core.db import db
from src.core.configuration import obtener_configuracion
from src.core.deliveries.turnos import a_hora_argentina, turno_actual


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


def _a_las(hora, minuto, segundo=0):
    """Arma un datetime de un día cualquiera a la hora indicada."""
    return datetime(2026, 10, 12, hora, minuto, segundo)


# Con los horarios iniciales

def test_mitad_de_cada_comida(app):
    assert turno_actual(_a_las(8, 0)) == "Desayuno"
    assert turno_actual(_a_las(13, 0)) == "Almuerzo"
    assert turno_actual(_a_las(17, 0)) == "Merienda"
    assert turno_actual(_a_las(21, 30)) == "Cena"


def test_bordes_cuentan_como_dentro(app):
    assert turno_actual(_a_las(6, 0)) == "Desayuno"
    assert turno_actual(_a_las(10, 0)) == "Desayuno"
    assert turno_actual(_a_las(10, 0, 45)) == "Desayuno"


def test_un_minuto_despues_del_borde(app):
    assert turno_actual(_a_las(10, 1)) is None


def test_madrugada(app):
    assert turno_actual(_a_las(3, 0)) is None


def test_entre_comidas(app):
    assert turno_actual(_a_las(15, 30)) is None


def test_a_hora_argentina_desde_utc_sin_zona():
    # Una cena del 13/10 a las 22:00 en Argentina queda guardada el 14/10 a la 01:00 UTC.
    assert a_hora_argentina(datetime(2026, 10, 14, 1, 0)).isoformat() == "2026-10-13T22:00:00-03:00"


# Con horarios cambiados en la configuración

def test_cambiar_inicio_del_almuerzo_cambia_la_comida_en_curso(app):
    configuracion = obtener_configuracion()
    configuracion.almuerzo_inicio = time(12, 30)
    db.session.commit()

    assert turno_actual(_a_las(12, 0)) is None
    assert turno_actual(_a_las(12, 30)) == "Almuerzo"


def test_adelantar_la_cena_cambia_la_comida_en_curso(app):
    configuracion = obtener_configuracion()
    configuracion.cena_inicio = time(19, 0)
    configuracion.cena_fin = time(22, 0)
    db.session.commit()

    assert turno_actual(_a_las(19, 30)) == "Cena"
    assert turno_actual(_a_las(22, 30)) is None
