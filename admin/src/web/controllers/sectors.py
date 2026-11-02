from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from src.core.sectors import (
    create_sector, 
    list_sectors, 
    update_sector, 
    get_sector, 
    toggle_status, 
    delete_sector,
    add_jefes_to_sector,
    remove_jefe_from_sector
    )
from src.core.sectors.exceptions import SectorAlreadyExistsError, SectorValidationError, SectorInactiveExistsError
from src.web.helpers.auth import permission_required
from src.core.users.models import User
from src.core.auth.models import Role
from src.web.helpers.paginacion import validar_pagina
from src.core.users import get_jefes_disponibles

sector_bp = Blueprint('sectors', __name__, url_prefix='/sectores')


@sector_bp.route('/', methods=['GET'])
@permission_required('sector_index')
def index():
    # Capturamos parámetros de la URL con valores por defecto
    page = validar_pagina(request.args.get('page')) or 1
    sort_by = request.args.get('sort_by', 'nombre')
    order = request.args.get('order', 'asc')

    # Parámetros de búsqueda
    search_nombre = request.args.get('search_nombre', '').strip()
    search_estado = request.args.get('search_estado', '').strip()
    search_jefe = request.args.get('search_jefe', '').strip()
    
    # Obtenemos los sectores paginados (máximo 25 por página)
    pagina_obj = list_sectors(
        page=page, 
        sort_by=sort_by, 
        order=order,
        search_nombre=search_nombre,
        search_estado=search_estado,
        search_jefe=search_jefe
    )

    jefes_disponibles = get_jefes_disponibles()
    
    
    return render_template(
        'sectors/sectors_list.html', 
        sectores=pagina_obj.items, 
        pagina=pagina_obj,         
        sort_by=sort_by,
        order=order,
        search_nombre=search_nombre,
        search_estado=search_estado,
        search_jefe=search_jefe,
        jefes_disponibles=jefes_disponibles
    ), 200

@sector_bp.route('/<int:id>', methods=['GET'])
@permission_required('sector_show')
def show(id):
    """Muestra el detalle completo de un sector."""
    sector = get_sector(id)
    
    # Si el usuario ingresa un ID que no existe en la URL, mostramos error 404
    if not sector:
        abort(404, description="El sector no existe o fue eliminado.")
        
    # Opcional: si querés mostrar los jefes asignados en la vista de detalle
    # asumiendo que tu modelo 'Sector' tiene la relación 'jefes' configurada
    
    return render_template(
        'sectors/sector_show.html', 
        sector=sector
    ), 200

@sector_bp.route('/nuevo', methods=['GET', 'POST'])
@permission_required('sector_create')
def create():
    errors = {}
    data = {'nombre': '', 'descripcion': '', 'jefes_ids': []}
    needs_confirmation = False
    # Buscar usuarios disponibles (activos, sin sector, y con rol 'jefe_servicio')
    jefes_disponibles = get_jefes_disponibles()

    status_code = 200

    if request.method == 'POST':
        data['nombre'] = request.form.get('nombre', '').strip()
        data['descripcion'] = request.form.get('descripcion', '').strip()
        data['jefes_ids'] = request.form.getlist('jefes_ids', type=int)
        reactivar_confirmado = request.form.get('confirmar_reactivacion') == 'true'

        # Validación sintáctica inicial en el controlador
        if not data['nombre']:
            errors['nombre'] = 'El nombre del sector es obligatorio.'
            status_code = 400
        elif len(data['nombre']) > 255:
            errors['nombre'] = 'El nombre no puede superar los 255 caracteres.'
            status_code = 400

        if not data['descripcion']:
            errors['descripcion'] = 'La descripción del sector es obligatoria.'
            status_code = 400
        elif len(data['descripcion']) > 1000:
            errors['descripcion'] = 'La descripción no puede superar los 1000 caracteres.'
            status_code = 400

        
        if not errors:
            try:
                sector_creado, advertencias = create_sector(
                    nombre=data['nombre'],
                    descripcion=data['descripcion'],
                    jefes_ids=data['jefes_ids'],
                    reactivar=reactivar_confirmado
                )
                
                flash('Operación realizada exitosamente.', 'success')
                
                # Informamos las asignaciones que fallaron
                for advertencia in advertencias:
                    flash(advertencia, 'warning')
                    
                return redirect(url_for('sectors.index'))

            except SectorInactiveExistsError as err:
                # Atrapamos que está inactivo y activamos la bandera para el HTML
                needs_confirmation = True
                flash("Atención requerida.", "warning")
                status_code = 409

            except SectorAlreadyExistsError as err:
                errors['nombre'] = str(err)
                status_code = 409

            except SectorValidationError as err:
                flash(str(err), 'error')
                status_code = 400

            except Exception as e:
                # Importamos traceback temporalmente para ver la ruta completa del error
                import traceback
                traceback.print_exc() 
                flash(f'Ocurrió un error inesperado: {str(e)}', 'error')
                status_code = 500

    return render_template(
        'sectors/sector_create.html', 
        data=data, 
        errors=errors,
        jefes_disponibles=jefes_disponibles,
        needs_confirmation=needs_confirmation
        ), status_code

@sector_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@permission_required('sector_update')
def edit(id):
    sector = get_sector(id)
    if not sector:
        abort(404, description="El sector no existe o fue eliminado.")

    jefes_disponibles = get_jefes_disponibles()
    errors = {}
    status_code = 200

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        jefes_ids = request.form.getlist('jefes_ids', type=int)

        try:
            sector_actualizado, advertencias = update_sector(
                id, 
                nombre=nombre, 
                descripcion=descripcion, 
                jefes_ids=jefes_ids
            )
            
            flash("El sector fue modificado exitosamente.", "success")
            
            # 3. Disparamos alertas amarillas por cada jefe inválido (si los hay)
            for adv in advertencias:
                flash(adv, 'warning')
                
            return redirect(url_for('sectors.index'))
            
        except SectorAlreadyExistsError as e:
            errors['nombre'] = str(e)
            status_code = 409
            
        except SectorValidationError as e:
            mensaje = str(e)
            if "descripción" in mensaje.lower():
                errors['descripcion'] = mensaje
            else:
                errors['nombre'] = mensaje
            status_code = 400
                
        except Exception as e:
            # Imprimimos en consola para debug y mostramos error general
            import traceback
            traceback.print_exc()
            errors['general'] = "Ocurrió un error inesperado al procesar la solicitud."
            status_code = 500

        data = {
            'nombre': nombre,
            'descripcion': descripcion,
            'jefes_ids': jefes_ids,
        }

        return render_template(
            'sectors/sector_edit.html', 
            sector=sector, 
            data=data, 
            errors=errors,
            jefes_disponibles=jefes_disponibles # 4. Lo pasamos al HTML
        ), status_code

    return render_template(
        'sectors/sector_edit.html', 
        sector=sector, 
        data={}, 
        errors={}, 
        jefes_disponibles=jefes_disponibles # 4. Lo pasamos al HTML
    ), 200

@sector_bp.route('/<int:id>/toggle', methods=['POST'])
@permission_required('sector_update')
def toggle(id):
    try:
        sector = toggle_status(id)
        accion = "activado" if sector.activo else "desactivado"
        flash(f"El sector '{sector.nombre}' fue {accion} exitosamente.", "success")
        return redirect(url_for('sectors.index')) # 302 Éxito
        
    except SectorValidationError as e:
        flash(str(e), "error")
        html, _ = index() # Renderizamos el listado
        return html, 400  # 400 Bad Request
        
    except Exception:
        flash("Ocurrió un error inesperado al intentar cambiar el estado del sector.", "error")
        html, _ = index()
        return html, 500  # 500 Internal Server Error

@sector_bp.route('/<int:id>/eliminar', methods=['POST'])
@permission_required('sector_destroy')
def delete(id):
    try:
        eliminado_fisicamente, mensaje = delete_sector(id)
        if eliminado_fisicamente:
            flash(mensaje, "success")
        else:
            flash(mensaje, "warning")
        return redirect(url_for('sectors.index')) # 302 Éxito
            
    except SectorValidationError as e:
        flash(str(e), "error")
        html, _ = index()
        return html, 400
        
    except Exception:
        flash("Ocurrió un error inesperado al intentar eliminar el sector.", "error")
        html, _ = index()
        return html, 500

@sector_bp.route('/<int:id>/jefes/asignar', methods=['POST'])
@permission_required('sector_update')
def assign_jefes(id):
    jefes_ids = request.form.getlist('jefes_ids', type=int)
    try:
        sector, advertencias = add_jefes_to_sector(id, jefes_ids)
        flash("Jefe(s) asignado(s) correctamente.", "success")
        for adv in advertencias:
            flash(adv, 'warning')
        return redirect(url_for('sectors.index')) # 302 Éxito
        
    except Exception as e:
        flash(f"Error al asignar: {str(e)}", "error")
        html, _ = index()
        return html, 400 # 400 Bad Request

@sector_bp.route('/<int:id>/jefes/<int:jefe_id>/desvincular', methods=['POST'])
@permission_required('sector_update')
def unassign_jefe(id, jefe_id):
    try:
        remove_jefe_from_sector(id, jefe_id)
        flash("Jefe de servicio desvinculado del sector.", "success")
        return redirect(url_for('sectors.index')) # 302 Éxito
        
    except Exception as e:
        flash(f"Error al desvincular: {str(e)}", "error")
        html, _ = index()
        return html, 400 # 400 Bad Request
