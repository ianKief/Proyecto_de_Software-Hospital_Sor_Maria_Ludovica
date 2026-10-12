from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.core.sectors import create_sector, list_sectors, update_sector, get_sector, toggle_status, delete_sector
from src.core.sectors.exceptions import SectorAlreadyExistsError, SectorValidationError
from src.web.helpers.auth import permission_required
from src.core.users.models import User
from src.core.auth.models import Role

sector_bp = Blueprint('sectors', __name__, url_prefix='/sectores')

# Agregá esta ruta en src/web/controllers/sector.py

@sector_bp.route('/', methods=['GET'])
@permission_required('sector_index')
def index():
    # Capturamos parámetros de la URL con valores por defecto
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nombre')
    order = request.args.get('order', 'asc')

    # Parámetros de búsqueda
    search_nombre = request.args.get('search_nombre', '').strip()
    search_estado = request.args.get('search_estado', '').strip()
    search_jefe = request.args.get('search_jefe', '').strip()
    
    # Obtenemos los sectores paginados (máximo 25 por página)
    sectores_paginados = list_sectors(
        page=page, 
        per_page=25, 
        sort_by=sort_by, 
        order=order,
        search_nombre=search_nombre,
        search_estado=search_estado,
        search_jefe=search_jefe
    )
    
    return render_template(
        'sectors/sectors_list.html', 
        sectores=sectores_paginados,
        sort_by=sort_by,
        order=order,
        search_nombre=search_nombre,
        search_estado=search_estado,
        search_jefe=search_jefe
    )

@sector_bp.route('/nuevo', methods=['GET', 'POST'])
@permission_required('sector_create')
def create():
    errors = {}
    data = {'nombre': '', 'descripcion': '', 'jefes_ids': []}

    # Buscar usuarios disponibles (activos, sin sector, y con rol 'jefe_servicio')
    jefes_disponibles = User.query.join(Role).filter(
        User.sector_id == None, 
        User.activo == True,
        Role.name == 'jefe_servicio'  # Ajustar a 'name' si tu modelo Role usa name
    ).all()

    if request.method == 'POST':
        data['nombre'] = request.form.get('nombre', '').strip()
        data['descripcion'] = request.form.get('descripcion', '').strip()
        data['jefes_ids'] = request.form.getlist('jefes_ids', type=int)

        # Validación sintáctica inicial en el controlador
        if not data['nombre']:
            errors['nombre'] = 'El nombre del sector es obligatorio.'
        elif len(data['nombre']) > 255:
            errors['nombre'] = 'El nombre no puede superar los 255 caracteres.'

        if not data['descripcion']:
            errors['descripcion'] = 'La descripción del sector es obligatoria.'
        elif len(data['descripcion']) > 1000:
            errors['descripcion'] = 'La descripción no puede superar los 1000 caracteres.'

        # Si supera la validación inicial, delegamos al core
        if not errors:
            try:
                # Recibimos el sector y la lista de advertencias
                sector_creado, advertencias = create_sector(
                    nombre=data['nombre'],
                    descripcion=data['descripcion'],
                    jefes_ids=data['jefes_ids']
                )
                
                flash('El sector fue creado exitosamente.', 'success')
                
                # Informamos las asignaciones que fallaron
                for advertencia in advertencias:
                    flash(advertencia, 'warning')
                    
                return redirect(url_for('sectors.index'))

            except SectorAlreadyExistsError as err:
                errors['nombre'] = str(err)

            except SectorValidationError as err:
                flash(str(err), 'error')

            except Exception as e:
                # Importamos traceback temporalmente para ver la ruta completa del error
                import traceback
                traceback.print_exc() 
                
                # Le agregamos el mensaje real al flash para que lo veas en la pantalla
                flash(f'Ocurrió un error inesperado: {str(e)}', 'error')

    return render_template(
        'sectors/sector_create.html', 
        data=data, 
        errors=errors,
        jefes_disponibles=jefes_disponibles
        )

@sector_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@permission_required('sector_update')
def edit(id):
    sector = get_sector(id)
    if not sector:
        flash("El sector no existe o fue eliminado.", "error")
        return redirect(url_for('sectors.index'))

    errors = {}
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()

        try:
            update_sector(id, nombre=nombre, descripcion=descripcion)
            flash("El sector fue modificado exitosamente.", "success")
            return redirect(url_for('sectors.index'))
            
        except SectorAlreadyExistsError as e:
            errors['nombre'] = str(e)
            
        except SectorValidationError as e:
            mensaje = str(e)
            if "descripción" in mensaje.lower():
                errors['descripcion'] = mensaje
            else:
                errors['nombre'] = mensaje
                
        except Exception:
            errors['general'] = "Ocurrió un error inesperado al procesar la solicitud."

        return render_template(
            'sectors/sector_edit.html', 
            sector=sector, 
            data=request.form, 
            errors=errors
        )

    return render_template('sectors/sector_edit.html', sector=sector, data={}, errors={})

@sector_bp.route('/<int:id>/toggle', methods=['POST'])
@permission_required('sector_update')
def toggle(id):
    """Activa o desactiva un sector según su estado actual."""
    try:
        sector = toggle_status(id)
        accion = "activado" if sector.activo else "desactivado"
        flash(f"El sector '{sector.nombre}' fue {accion} exitosamente.", "success")
        
    except SectorValidationError as e:
        # Si falla la validación (ej. tiene personal o jefes activos), mostramos el error
        flash(str(e), "error")
        
    except Exception:
        flash("Ocurrió un error inesperado al intentar cambiar el estado del sector.", "error")

    # Siempre redirigimos al listado para ver el resultado
    return redirect(url_for('sectors.index'))

@sector_bp.route('/<int:id>/eliminar', methods=['POST'])
@permission_required('sector_destroy')
def delete(id):
    """
    Intenta eliminar un sector. Si tiene dependencias, el core lo desactivará
    automáticamente (Soft Delete).
    """
    try:
        eliminado_fisicamente, mensaje = delete_sector(id)
        
        if eliminado_fisicamente:
            # Borrado definitivo de la base de datos (Color verde)
            flash(mensaje, "success")
        else:
            # No se pudo borrar pero fue desactivado (Color amarillo/naranja)
            flash(mensaje, "warning")
            
    except SectorValidationError as e:
        # Entra acá si ya estaba inactivo y tampoco se puede borrar, o si no existe
        flash(str(e), "error")
        
    except Exception:
        flash("Ocurrió un error inesperado al intentar eliminar el sector.", "error")

    return redirect(url_for('sectors.index'))