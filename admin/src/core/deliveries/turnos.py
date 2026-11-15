"""Turnos de comida: el rango horario en que se sirve cada comida."""
from datetime import datetime, timezone

# ZONA_ARGENTINA está definida en configuration (la usa también pedido_editable)
# y se importa desde acá para que Entregas la siga encontrando en turnos.
from src.core.configuration import ZONA_ARGENTINA, obtener_configuracion


def horarios_de_comidas():
    """Devuelve el horario de cada comida según la configuración del sistema.

    Clave: nombre exacto de FoodType (seed de init_db.py).
    Valor: (inicio, fin) como ``datetime.time``, los dos incluidos.
    Se lee de la base cada vez, así un cambio en Ajustes se aplica enseguida.
    """
    configuracion = obtener_configuracion()
    return {
        "Desayuno": (configuracion.desayuno_inicio, configuracion.desayuno_fin),
        "Almuerzo": (configuracion.almuerzo_inicio, configuracion.almuerzo_fin),
        "Merienda": (configuracion.merienda_inicio, configuracion.merienda_fin),
        "Cena": (configuracion.cena_inicio, configuracion.cena_fin),
    }


def hora_actual():
    """Devuelve la fecha y hora actual en Argentina (UTC-3).

    Todo Entregas toma la hora de acá, así no depende de la zona horaria del servidor.
    """
    return datetime.now(ZONA_ARGENTINA)


def hoy():
    """Devuelve la fecha actual en Argentina que usa el módulo de Entregas."""
    return hora_actual().date()


def a_hora_argentina(dt):
    """Pasa un datetime guardado en UTC a la hora de Argentina (UTC-3).

    Las columnas ``created_at`` son ``DateTime`` sin zona y guardan la hora en UTC,
    así que la base las devuelve sin ``tzinfo``: en ese caso se le indica que es
    UTC antes de convertirlo. Si ya trae zona, se convierte directamente.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZONA_ARGENTINA)


def turno_actual(ahora):
    """Devuelve el nombre de la comida que se sirve en ``ahora`` (un datetime), o None si no hay ninguna.

    Los bordes cuentan como dentro del turno: a las 10:00 todavía es Desayuno.
    Se compara por hora y minuto (se ignoran segundos), así 10:00:45 también es Desayuno.
    No llama a datetime.now(): quien la usa le pasa la hora, y así se puede testear.
    Los horarios salen de la configuración, así que necesita la app y la base.
    """
    hora = ahora.time().replace(second=0, microsecond=0)
    for comida, (inicio, fin) in horarios_de_comidas().items():
        if inicio <= hora <= fin:
            return comida
    return None
