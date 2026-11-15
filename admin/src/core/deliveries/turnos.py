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


def _hora_sin_segundos(ahora):
    """Devuelve la hora de ``ahora`` (un datetime) sin segundos ni microsegundos.

    Los horarios de la configuración son de hora y minuto: así el minuto
    del borde cuenta entero (10:00:45 todavía es las 10:00).
    """
    return ahora.time().replace(second=0, microsecond=0)


def turno_actual(ahora):
    """Devuelve el nombre de la comida que se sirve en ``ahora`` (un datetime), o None si no hay ninguna.

    Los bordes cuentan como dentro del turno: a las 10:00 todavía es Desayuno.
    Se compara por hora y minuto (se ignoran segundos), así 10:00:45 también es Desayuno.
    No llama a datetime.now(): quien la usa le pasa la hora, y así se puede testear.
    Los horarios salen de la configuración, así que necesita la app y la base.
    """
    hora = _hora_sin_segundos(ahora)
    for comida, (inicio, fin) in horarios_de_comidas().items():
        if inicio <= hora <= fin:
            return comida
    return None


def hora_de_fin(comida):
    """Devuelve la hora de fin de ``comida`` (su nombre) según la configuración.

    Devuelve ``None`` si esa comida no tiene horario en la configuración
    (un tipo de comida con un nombre distinto a los cuatro del seed).
    """
    horario = horarios_de_comidas().get(comida)
    if horario is None:
        return None

    inicio, fin = horario
    return fin


def comida_terminada(fin, ahora):
    """Indica si en ``ahora`` (un datetime) ya pasó la hora de fin ``fin`` de una comida.

    El borde cuenta como no terminado, igual que en ``turno_actual``: con
    fin a las 15:00, a las 15:00:45 todavía se puede entregar y a las 15:01 no.
    Recibe el ``fin`` (y no el nombre de la comida) para que quien la llama
    use la misma hora en el mensaje de error.
    """
    return _hora_sin_segundos(ahora) > fin
