from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from src.core import personnel
from src.core.personnel.validators import ValidationError
from src.web.helpers.paginacion import validar_pagina
from src.web.helpers.auth import permission_required

bp = Blueprint("personnel", __name__, url_prefix="/personal")


@bp.get("/")
@permission_required("personnel_index")
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
@permission_required("personnel_new")
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
@permission_required("personnel_new")
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
            "personnel/alta.html",
            tipos_personal=tipos_personal,
            tipos_menu=tipos_menu,
            sectores=sectores,
            data=data,
        )


@bp.get("/<int:personnel_id>/editar")
@permission_required("personnel_update")
def edit(personnel_id: int):
    persona = personnel.get_personnel_by_id(personnel_id)
    if not persona:
        flash("La persona solicitada no existe.", "error")
        return redirect(url_for("personnel.index"))

    tipos_personal = personnel.list_personnel_types()
    tipos_menu = personnel.list_menu_types()
    sectores = personnel.list_active_sectors()

    data = {
        "dni": persona.dni,
        "nombre": persona.nombre,
        "apellido": persona.apellido,
        "personnel_type_id": str(persona.personnel_type_id),
        "sector_id": str(persona.sector_id) if persona.sector_id else "",
        "menu_type_id": str(persona.menu_type_id),
        "activo": "true" if persona.activo else "false",
    }

    return render_template(
        "personnel/editar.html",
        persona=persona,
        tipos_personal=tipos_personal,
        tipos_menu=tipos_menu,
        sectores=sectores,
        data=data,
    )


@bp.post("/<int:personnel_id>/editar")
@permission_required("personnel_update")
def update(personnel_id: int):
    data = request.form.to_dict()
    try:
        persona = personnel.update_personnel(personnel_id, data)
        flash(f"Personal {persona.nombre} {persona.apellido} actualizado con éxito.", "success")
        return redirect(url_for("personnel.index"))
    except ValidationError as e:
        flash(str(e), "error")
        persona = personnel.get_personnel_by_id(personnel_id)
        tipos_personal = personnel.list_personnel_types()
        tipos_menu = personnel.list_menu_types()
        sectores = personnel.list_active_sectors()
        return render_template(
            "personnel/editar.html",
            persona=persona,
            tipos_personal=tipos_personal,
            tipos_menu=tipos_menu,
            sectores=sectores,
            data=data,
        )


@bp.post("/<int:personnel_id>/eliminar")
@permission_required("personnel_destroy")
def delete(personnel_id: int):
    try:
        es_fisica, mensaje = personnel.delete_personnel(personnel_id)
        flash(mensaje, "success" if es_fisica else "warning")
    except ValidationError as e:
        flash(str(e), "error")
    return redirect(url_for("personnel.index"))

@bp.get("/importar")
@permission_required("personnel_import")
def import_csv():
    return render_template("personnel/importar.html", resultado=None)


@bp.post("/importar")
@permission_required("personnel_import")
def process_import_csv():
    if "archivo_csv" not in request.files:
        flash("No se ha enviado ningún archivo.", "error")
        return redirect(url_for("personnel.import_csv"))

    archivo = request.files["archivo_csv"]
    if not archivo or archivo.filename == "":
        flash("Debe seleccionar un archivo .csv.", "error")
        return redirect(url_for("personnel.import_csv"))

    if not archivo.filename.lower().endswith(".csv"):
        flash("El archivo seleccionado debe ser de extensión .csv", "error")
        return redirect(url_for("personnel.import_csv"))

    resultado = personnel.importar_personal_csv(archivo.stream)

    if resultado["importados"] > 0:
        flash(f"Se importaron exitosamente {resultado['importados']} registros.", "success")
    if resultado["rechazados"] > 0:
        flash(f"Se rechazaron {resultado['rechazados']} registros. Revise los motivos detallados abajo.", "error")

    return render_template("personnel/importar.html", resultado=resultado)

@bp.get("/plantilla-csv")
@permission_required("personnel_import")
def download_template_csv():
    """Genera y descarga un CSV de ejemplo listo para completar."""
    columnas = "dni,nombre,apellido,tipo_personal,tipo_menu,sector\n"
    ejemplo = "40111222,Juan,Perez,Planta Permanente,General,Urgencias\n"
    return Response(
        columnas + ejemplo,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_personal.csv"},
    )