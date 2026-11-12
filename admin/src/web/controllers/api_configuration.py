"""API de la configuración general del sistema."""
from flask import Blueprint, jsonify

from src.core.configuration import obtener_configuracion, hora_a_texto

# El prefijo es "/api" y la ruta "/configuration" para que la URL sea
# exactamente /api/configuration (sin barra final, que daría una redirección).
api_configuration_bp = Blueprint("api_configuration", __name__, url_prefix="/api")


def _comidas_en_json(configuracion):
    """Arma el horario de inicio y fin de cada comida, como texto "HH:MM"."""
    return {
        "desayuno": {
            "inicio": hora_a_texto(configuracion.desayuno_inicio),
            "fin": hora_a_texto(configuracion.desayuno_fin),
        },
        "almuerzo": {
            "inicio": hora_a_texto(configuracion.almuerzo_inicio),
            "fin": hora_a_texto(configuracion.almuerzo_fin),
        },
        "merienda": {
            "inicio": hora_a_texto(configuracion.merienda_inicio),
            "fin": hora_a_texto(configuracion.merienda_fin),
        },
        "cena": {
            "inicio": hora_a_texto(configuracion.cena_inicio),
            "fin": hora_a_texto(configuracion.cena_fin),
        },
    }


@api_configuration_bp.get("/configuration")
def configuration_show():
    """Devuelve en JSON los ajustes del sistema.

    Es pública (no pide token): el portal la consulta antes del login para
    saber si el sitio está en mantenimiento y si hay conexión con el servidor.
    Por eso solo devuelve parámetros generales, sin ids ni datos de usuarios.
    ``mensaje_mantenimiento`` sale ``null`` si no hay mensaje guardado.
    """
    configuracion = obtener_configuracion()
    return jsonify({
        "elementos_por_pagina": configuracion.elementos_por_pagina,
        "mantenimiento_activo": configuracion.mantenimiento_activo,
        "mensaje_mantenimiento": configuracion.mensaje_mantenimiento,
        "horario_corte": hora_a_texto(configuracion.horario_corte),
        "comidas": _comidas_en_json(configuracion),
    }), 200
