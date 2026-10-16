from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from src.core import quotas
from src.core.quotas.validators import ValidationError
from src.core.sectors.models import Sector
from src.core.users.models import User
from src.core.paginacion import paginar
from src.web.helpers.paginacion import validar_pagina
from src.web.helpers.auth import permission_required

bp = Blueprint("quotas", __name__, url_prefix="/cupos")


def _obtener_usuario_actual():
    """Recupera la instancia del usuario autenticado en la sesión actual."""
    user_id = session.get("user_id")
    if user_id:
        return User.query.get(user_id)
    return None


@bp.get("/")
@permission_required("quota_index")
def index():
    user = _obtener_usuario_actual()
    es_jefe = user and user.role and user.role.name == "Jefe de Servicio"

    # Si es Jefe de Servicio, se fuerza estrictamente el sector asignado al usuario
    if es_jefe:
        sector_id = user.sector_id
    else:
        sector_id = request.args.get("sector_id", type=int)

    tipo_comida_id = request.args.get("tipo_comida_id", type=int)
    order = request.args.get("order", "asc")
    numero_pagina = validar_pagina(request.args.get("page")) or 1

    query = quotas.list_quotas(
        sector_id=sector_id,
        tipo_comida_id=tipo_comida_id,
        order=order,
    )

    pagina = paginar(query, numero_pagina)

    # Si es jefe de servicio, solo ve su sector en el selector; si no, todos los activos
    if es_jefe:
        sectores = [user.sector] if user.sector else []
    else:
        sectores = Sector.query.filter_by(activo=True).order_by(Sector.nombre.asc()).all()

    tipos_comida = quotas.list_food_types()

    return render_template(
        "quotas/listado.html",
        cupos=pagina.items,
        pagina=pagina,
        sectores=sectores,
        tipos_comida=tipos_comida,
        sector_id=sector_id,
        tipo_comida_id=tipo_comida_id,
        order=order,
        es_jefe=es_jefe,
    )


@bp.get("/nuevo")
@permission_required("quota_new")
def new():
    sectores = quotas.list_active_sectors()
    tipos_comida = quotas.list_food_types()
    return render_template(
        "quotas/alta.html",
        sectores=sectores,
        tipos_comida=tipos_comida,
        data={},
    )


@bp.post("/nuevo")
@permission_required("quota_new")
def create():
    data = request.form.to_dict()
    try:
        nuevo_cupo = quotas.create_quota(data)
        flash(
            f"Cupo para '{nuevo_cupo.sector.nombre}' ({nuevo_cupo.tipo_comida.nombre}) creado con éxito.",
            "success",
        )
        return redirect(url_for("quotas.index"))
    except ValidationError as e:
        flash(str(e), "error")
        sectores = quotas.list_active_sectors()
        tipos_comida = quotas.list_food_types()
        return render_template(
            "quotas/alta.html",
            sectores=sectores,
            tipos_comida=tipos_comida,
            data=data,
        )


@bp.get("/<int:quota_id>/editar")
@permission_required("quota_update")
def edit(quota_id: int):
    cupo = quotas.get_quota_by_id(quota_id)
    if not cupo:
        flash("El cupo solicitado no existe.", "error")
        return redirect(url_for("quotas.index"))

    sectores = quotas.list_active_sectors()
    if cupo.sector not in sectores:
        sectores.append(cupo.sector)

    tipos_comida = quotas.list_food_types()
    data = {
        "sector_id": str(cupo.sector_id),
        "tipo_comida_id": str(cupo.tipo_comida_id),
        "cantidad": str(cupo.cantidad),
    }

    return render_template(
        "quotas/editar.html",
        cupo=cupo,
        sectores=sectores,
        tipos_comida=tipos_comida,
        data=data,
    )


@bp.post("/<int:quota_id>/editar")
@permission_required("quota_update")
def update(quota_id: int):
    data = request.form.to_dict()
    try:
        cupo = quotas.update_quota(quota_id, data)
        flash(
            f"Cupo de '{cupo.sector.nombre}' ({cupo.tipo_comida.nombre}) actualizado con éxito.",
            "success",
        )
        return redirect(url_for("quotas.index"))
    except ValidationError as e:
        flash(str(e), "error")
        cupo = quotas.get_quota_by_id(quota_id)
        sectores = quotas.list_active_sectors()
        if cupo and cupo.sector not in sectores:
            sectores.append(cupo.sector)
        tipos_comida = quotas.list_food_types()
        return render_template(
            "quotas/editar.html",
            cupo=cupo,
            sectores=sectores,
            tipos_comida=tipos_comida,
            data=data,
        )


@bp.post("/<int:quota_id>/eliminar")
@permission_required("quota_destroy")
def delete(quota_id: int):
    try:
        quotas.delete_quota(quota_id)
        flash("El cupo fue eliminado con éxito.", "success")
    except ValidationError as e:
        flash(str(e), "error")
    return redirect(url_for("quotas.index"))