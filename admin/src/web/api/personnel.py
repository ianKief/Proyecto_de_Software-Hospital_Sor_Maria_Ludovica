from flask import Blueprint, jsonify, request, g
from src.core import personnel
from src.core.personnel.models import Personal
from src.core.personnel_types.models import PersonnelType
from src.core.personnel.validators import ValidationError
from src.web.helpers.api_auth import api_permission_required

api_personnel_bp = Blueprint("api_personnel", __name__, url_prefix="/api/personnel")


def _get_user(current_user=None):
    return current_user or getattr(g, "user", None) or getattr(g, "current_user", None)


def _es_jefe_servicio(user):
    if not user:
        return False
    rol_obj = getattr(user, "role", None)
    rol_nombre = getattr(rol_obj, "name", str(rol_obj)) if rol_obj else getattr(user, "role_name", "")
    return "jefe" in str(rol_nombre).lower()


def _serializar_persona(p):
    return {
        "id": p.id,
        "dni": p.dni,
        "nombre": p.nombre,
        "apellido": p.apellido,
        "activo": p.activo,
        "tipo_personal": {
            "id": p.personnel_type.id,
            "nombre": p.personnel_type.nombre,
        } if getattr(p, "personnel_type", None) else None,
        "sector": {
            "id": p.sector.id,
            "nombre": p.sector.nombre,
        } if getattr(p, "sector", None) else None,
        "tipo_menu": {
            "id": p.menu_type.id,
            "nombre": p.menu_type.nombre,
        } if getattr(p, "menu_type", None) else None,
    }


@api_personnel_bp.route("/", methods=["GET"])
@api_permission_required("personnel_index")
def list_personnel_api(current_user=None, **kwargs):
    user = _get_user(current_user)
    es_jefe = _es_jefe_servicio(user)

    dni = request.args.get("dni", "").strip()
    nombre_apellido = request.args.get("nombre_apellido", "").strip()
    tp_id_raw = request.args.get("personnel_type_id")
    tp_id = int(tp_id_raw) if tp_id_raw and tp_id_raw.isdigit() else None

    resultado = personnel.list_personnel(
        dni=dni,
        nombre_apellido=nombre_apellido,
        personnel_type_id=tp_id,
    )

    items = resultado.items if hasattr(resultado, "items") else resultado

    if es_jefe:
        sector_id_jefe = getattr(user, "sector_id", None)
        filtrados = []
        for p in items:
            tp_nombre = p.personnel_type.nombre.lower() if getattr(p, "personnel_type", None) else ""
            es_residente = "residente" in tp_nombre
            # Jefe de Servicio solo ve personal de su sector o residentes
            if p.sector_id == sector_id_jefe or es_residente:
                filtrados.append(p)
        items = filtrados

    items_serializados = [_serializar_persona(p) for p in items]

    if hasattr(resultado, "total"):
        return jsonify({
            "items": items_serializados,
            "total": len(items_serializados),
            "page": getattr(resultado, "page", 1),
            "pages": getattr(resultado, "pages", 1),
        }), 200

    return jsonify({"items": items_serializados, "total": len(items_serializados)}), 200


@api_personnel_bp.route("/<int:person_id>", methods=["GET"])
@api_permission_required("personnel_show")
def get_personnel_api(person_id, current_user=None, **kwargs):
    persona = personnel.get_personnel_by_id(person_id)
    if not persona:
        return jsonify({"error": "La persona no existe."}), 404

    user = _get_user(current_user)
    if _es_jefe_servicio(user):
        tp_nombre = persona.personnel_type.nombre.lower() if getattr(persona, "personnel_type", None) else ""
        es_residente = "residente" in tp_nombre
        if persona.sector_id != getattr(user, "sector_id", None) and not es_residente:
            return jsonify({"error": "No tiene permisos para consultar personal de otro sector."}), 403

    return jsonify(_serializar_persona(persona)), 200


@api_personnel_bp.route("/", methods=["POST"])
@api_permission_required("personnel_new")
def create_personnel_api(current_user=None, **kwargs):
    user = _get_user(current_user)
    data = request.get_json() or {}

    if _es_jefe_servicio(user):
        data["sector_id"] = getattr(user, "sector_id", None)
        tp_id = data.get("personnel_type_id")
        tp = PersonnelType.query.filter_by(id=tp_id).first() if tp_id else None
        if tp and "residente" in tp.nombre.lower():
            return jsonify({"error": "El Jefe de Servicio no puede crear personal de tipo Residente."}), 403

    dni = str(data.get("dni", "")).strip()
    if Personal.query.filter_by(dni=dni).first():
        return jsonify({"error": "Ya existe una persona registrada con ese DNI."}), 409

    try:
        nueva_persona = personnel.create_personnel(data)
        return jsonify(_serializar_persona(nueva_persona)), 201
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400


@api_personnel_bp.route("/<int:person_id>", methods=["PUT"])
@api_permission_required("personnel_update")
def update_personnel_api(person_id, current_user=None, **kwargs):
    persona = personnel.get_personnel_by_id(person_id)
    if not persona:
        return jsonify({"error": "La persona no existe."}), 404

    user = _get_user(current_user)
    if _es_jefe_servicio(user):
        tp_nombre = persona.personnel_type.nombre.lower() if getattr(persona, "personnel_type", None) else ""
        es_residente = "residente" in tp_nombre
        if persona.sector_id != getattr(user, "sector_id", None) or es_residente:
            return jsonify({"error": "No posee permisos para modificar este personal."}), 403

    data = request.get_json() or {}
    dni = str(data.get("dni", "")).strip()
    otro = Personal.query.filter_by(dni=dni).first()
    if otro and otro.id != person_id:
        return jsonify({"error": "El DNI ingresado ya pertenece a otra persona."}), 409

    try:
        actualizada = personnel.update_personnel(person_id, data)
        return jsonify(_serializar_persona(actualizada)), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400


@api_personnel_bp.route("/<int:person_id>", methods=["DELETE"])
@api_permission_required("personnel_destroy")
def delete_personnel_api(person_id, current_user=None, **kwargs):
    persona = personnel.get_personnel_by_id(person_id)
    if not persona:
        return jsonify({"error": "La persona no existe."}), 404

    user = _get_user(current_user)
    if _es_jefe_servicio(user):
        tp_nombre = persona.personnel_type.nombre.lower() if getattr(persona, "personnel_type", None) else ""
        es_residente = "residente" in tp_nombre
        if persona.sector_id != getattr(user, "sector_id", None) or es_residente:
            return jsonify({"error": "No posee permisos para eliminar este personal."}), 403

    try:
        es_fisica, mensaje = personnel.delete_personnel(person_id)
        return jsonify({"mensaje": mensaje, "baja_fisica": es_fisica}), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400