from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.core import personnel
from src.core.personnel.validators import ValidationError
from src.web.helpers.paginacion import validar_pagina

bp = Blueprint("personnel", __name__, url_prefix="/personal")


@bp.get("/")
def index():
    # lee la pagina
    numero = validar_pagina(request.args.get("page")) or 1

    # lee el filtrado y orden
    dni = request.args.get("dni", "").strip()
    nombre_apellido = request.args.get("nombre_apellido", "").strip()
    
    sector_id_raw = request.args.get("sector_id", "")
    sector_id = int(sector_id_raw) if sector_id_raw.isdigit() else None

    personnel_type_id_raw = request.args.get("personnel_type_id", "")
    personnel_type_id = int(personnel_type_id_raw) if personnel_type_id_raw.isdigit() else None

    activo_raw = request.args.get("activo", "")
    activo = None
    if activo_raw in ["true", "1"]:
        activo = True
    elif activo_raw in ["false", "0"]:
        activo = False

    order_by = request.args.get("order_by", "apellido_nombre")
    order_direction = request.args.get("order_direction", "asc")

    # consulta paginada
    pagina = personnel.list_personnel(
        page=numero,
        dni=dni,
        nombre_apellido=nombre_apellido,
        sector_id=sector_id,
        personnel_type_id=personnel_type_id,
        activo=activo,
        order_by=order_by,
        order_direction=order_direction,
    )

    # catalogos para poblar los selects del buscador
    sectores = personnel.list_active_sectors()
    tipos_personal = personnel.list_personnel_types()

    return render_template(
        "personnel/listado.html",
        pagina=pagina,
        personal=pagina.items,
        sectores=sectores,
        tipos_personal=tipos_personal,
        dni=dni,
        nombre_apellido=nombre_apellido,
        sector_id=sector_id,
        personnel_type_id=personnel_type_id,
        activo=activo_raw,
        order_by=order_by,
        order_direction=order_direction,
    )


@bp.get("/nuevo")
def new():
    tipos_personal = personnel.list_personnel_types()
    tipos_menu = personnel.list_menu_types()
    sectores = personnel.list_active_sectors()
    return render_template(
        "personnel/alta.html",
        tipos_personal=tipos_personal,
        tipos_menu=tipos_menu,
        sectores=sectores,
        data={},
    )


@bp.post("/nuevo")
def create():
    data = request.form.to_dict()
    try:
        nueva_persona = personnel.create_personnel(data)
        flash(f"Personal {nueva_persona.nombre} {nueva_persona.apellido} creado con éxito.", "success")
        return redirect(url_for("personnel.index"))
    except ValidationError as e:
        flash(str(e), "error")
        tipos_personal = personnel.list_personnel_types()
        tipos_menu = personnel.list_menu_types()
        sectores = personnel.list_active_sectors()
        return render_template(
            "personnel/new.html",
            tipos_personal=tipos_personal,
            tipos_menu=tipos_menu,
            sectores=sectores,
            data=data,
        )