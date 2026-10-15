from flask import Blueprint, jsonify, request
from src.core.sectors import list_sectors, get_sector
from src.web.helpers.api_auth import api_permission_required

api_sector_bp = Blueprint('api_sectors', __name__, url_prefix='/api/sectors')

@api_sector_bp.route('/', methods=['GET'])
@api_permission_required('sector_index')  # Maneja el 401 y el 403 automáticamente
def list_sectors_api():
    """Listar sectores.
    Parámetro opcional: estado ('activo' o 'todos').
    """
    # Parámetro de query 'estado' (activo por defecto)[cite: 58]
    estado_param = request.args.get('estado', 'activo').lower()
    search_estado = '' if estado_param == 'todos' else 'activo'

    try:
        sectores_paginados = list_sectors(search_estado=search_estado)
        
        # Formateo de salida[cite: 58]
        resultado = []
        for sector in sectores_paginados.items:
            resultado.append({
                "id": sector.id,
                "nombre": sector.nombre,
                "descripcion": sector.descripcion,
                "estado": "activo" if sector.activo else "inactivo"
            })

        return jsonify(resultado), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error interno del servidor."}), 500


@api_sector_bp.route('/<int:sector_id>', methods=['GET'])
@api_permission_required('sector_show')  # Maneja el 401 y el 403 automáticamente
def get_sector_api(sector_id):
    """Obtener un sector por ID, incluyendo inactivos."""
    try:
        # Buscamos el sector por ID (sin restricción de estado)[cite: 58, 59]
        sector = get_sector(sector_id)
        
        # Error 404 si no existe[cite: 59]
        if not sector:
            return jsonify({"error": "El sector solicitado no existe."}), 404

        # Datos completos del sector[cite: 58]
        return jsonify({
            "id": sector.id,
            "nombre": sector.nombre,
            "descripcion": sector.descripcion,
            "estado": "activo" if sector.activo else "inactivo"
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error interno del servidor."}), 500