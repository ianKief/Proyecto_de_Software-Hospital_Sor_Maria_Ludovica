from flask import Blueprint, jsonify, request, g
from src.core import quotas
from src.core.quotas.validators import ValidationError
from src.web.helpers.api_auth import api_permission_required

api_quotas_bp = Blueprint("api_quotas", __name__, url_prefix="/api/quotas")


def _get_user(current_user=None):
    return current_user or getattr(g, "user", None) or getattr(g, "current_user", None)


def _es_jefe_servicio(user):
    if not user:
        return False
    rol_obj = getattr(user, "role", None)
    rol_nombre = getattr(rol_obj, "name", str(rol_obj)) if rol_obj else getattr(user, "role_name", "")
    return "jefe" in str(rol_nombre).lower()


def _serializar_cupo(cupo):
    return {
        "id": cupo.id,
        "sector_id": cupo.sector_id,
        "sector": cupo.sector.nombre if getattr(cupo, "sector", None) else None,
        "tipo_comida_id": getattr(cupo, "food_type_id", getattr(cupo, "tipo_comida_id", None)),
        "tipo_comida": cupo.food_type.nombre if getattr(cupo, "food_type", None) else (
            cupo.tipo_comida.nombre if getattr(cupo, "tipo_comida", None) else None
        ),
        "cantidad": cupo.cantidad,
    }


@api_quotas_bp.route("/", methods=["GET"])
@api_permission_required("quota_index")
def list_quotas_api(current_user=None, **kwargs):
    user = _get_user(current_user)
    es_jefe = _es_jefe_servicio(user)

    sector_id_param = request.args.get("sector_id")
    sector_id = int(sector_id_param) if sector_id_param and sector_id_param.isdigit() else None

    if es_jefe:
        user_sector = getattr(user, "sector_id", None)
        if sector_id is not None and sector_id != user_sector:
            return jsonify({"error": "No tiene permisos para ver cupos de otro sector."}), 403
        sector_id = user_sector

    tipo_comida_id = request.args.get("tipo_comida_id", type=int) or request.args.get("food_type_id", type=int)

    try:
        resultado = quotas.list_quotas(sector_id=sector_id, tipo_comida_id=tipo_comida_id)
    except TypeError:
        resultado = quotas.list_quotas()

    items = resultado.items if hasattr(resultado, "items") else resultado

    if es_jefe:
        user_sector = getattr(user, "sector_id", None)
        items = [c for c in items if c.sector_id == user_sector]

    items_serializados = [_serializar_cupo(c) for c in items]

    return jsonify({
        "items": items_serializados,
        "total": len(items_serializados),
    }), 200


@api_quotas_bp.route("/<int:quota_id>", methods=["GET"])
@api_permission_required("quota_show")
def get_quota_api(quota_id, current_user=None, **kwargs):
    cupo = quotas.get_quota_by_id(quota_id)
    if not cupo:
        return jsonify({"error": "El cupo no existe."}), 404

    user = _get_user(current_user)
    if _es_jefe_servicio(user) and cupo.sector_id != getattr(user, "sector_id", None):
        return jsonify({"error": "No tiene permisos para consultar este cupo."}), 403

    return jsonify(_serializar_cupo(cupo)), 200


@api_quotas_bp.route("/", methods=["POST"])
@api_permission_required("quota_new")
def create_quota_api(current_user=None, **kwargs):
    user = _get_user(current_user)
    if _es_jefe_servicio(user):
        return jsonify({"error": "El Jefe de Servicio no puede crear cupos."}), 403

    data = request.get_json() or {}
    try:
        nuevo_cupo = quotas.create_quota(data)
        return jsonify(_serializar_cupo(nuevo_cupo)), 201
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400


@api_quotas_bp.route("/<int:quota_id>", methods=["PUT"])
@api_permission_required("quota_update")
def update_quota_api(quota_id, current_user=None, **kwargs):
    user = _get_user(current_user)
    if _es_jefe_servicio(user):
        return jsonify({"error": "El Jefe de Servicio no puede modificar cupos."}), 403

    data = request.get_json() or {}
    try:
        cupo_actualizado = quotas.update_quota(quota_id, data)
        return jsonify(_serializar_cupo(cupo_actualizado)), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400