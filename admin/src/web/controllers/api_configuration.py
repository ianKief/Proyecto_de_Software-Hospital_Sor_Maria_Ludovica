"""API de la configuración general del sistema."""
from flask import Blueprint, jsonify

from src.core.configuration import obtener_configuracion
from src.web.helpers.api_auth import api_permission_required

# El prefijo es "/api" y la ruta "/configuration" para que la URL sea
# exactamente /api/configuration (sin barra final, que daría una redirección).
api_configuration_bp = Blueprint("api_configuration", __name__, url_prefix="/api")


@api_configuration_bp.get("/configuration")
@api_permission_required("config_show")
def configuration_show():
    """Devuelve en JSON los ajustes del sistema.

    Lo puede pedir cualquier usuario con sesión (no hace falta un permiso).
    ``mensaje_mantenimiento`` sale ``null`` si no hay mensaje guardado.
    """
    configuracion = obtener_configuracion()
    return jsonify({
        "elementos_por_pagina": configuracion.elementos_por_pagina,
        "mantenimiento_activo": configuracion.mantenimiento_activo,
        "mensaje_mantenimiento": configuracion.mensaje_mantenimiento,
    }), 200
