"""Turnos de comida: el rango horario en que se sirve cada comida."""
from datetime import time

# Clave: nombre exacto de FoodType (seed de init_db.py). Valor: (inicio, fin), los dos incluidos.
TURNOS = {
    "Desayuno": (time(6, 0), time(10, 0)),
    "Almuerzo": (time(11, 30), time(15, 0)),
    "Merienda": (time(16, 0), time(18, 30)),
    "Cena": (time(20, 0), time(23, 0)),
}


def turno_actual(ahora):
    """Devuelve el nombre de la comida que se sirve en ``ahora`` (un datetime), o None si no hay ninguna.

    Los bordes cuentan como dentro del turno: a las 10:00 todavía es Desayuno.
    Se compara por hora y minuto (se ignoran segundos), así 10:00:45 también es Desayuno.
    No llama a datetime.now(): quien la usa le pasa la hora, y así se puede testear.
    """
    hora = ahora.time().replace(second=0, microsecond=0)
    for comida, (inicio, fin) in TURNOS.items():
        if inicio <= hora <= fin:
            return comida
    return None
