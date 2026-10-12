"""Tests de los turnos de comida (no necesitan base de datos)."""
from datetime import datetime

from src.core.deliveries.turnos import turno_actual


def _a_las(hora, minuto, segundo=0):
    """Arma un datetime de un día cualquiera a la hora indicada."""
    return datetime(2026, 10, 12, hora, minuto, segundo)


def test_mitad_de_cada_comida():
    assert turno_actual(_a_las(8, 0)) == "Desayuno"
    assert turno_actual(_a_las(13, 0)) == "Almuerzo"
    assert turno_actual(_a_las(17, 0)) == "Merienda"
    assert turno_actual(_a_las(21, 30)) == "Cena"


def test_bordes_cuentan_como_dentro():
    assert turno_actual(_a_las(6, 0)) == "Desayuno"
    assert turno_actual(_a_las(10, 0)) == "Desayuno"
    assert turno_actual(_a_las(10, 0, 45)) == "Desayuno"


def test_un_minuto_despues_del_borde():
    assert turno_actual(_a_las(10, 1)) is None


def test_madrugada():
    assert turno_actual(_a_las(3, 0)) is None


def test_entre_comidas():
    assert turno_actual(_a_las(15, 30)) is None
