from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.core.sectors import create_sector
from src.core.sectors.exceptions import SectorAlreadyExistsError, SectorValidationError
from src.web.helpers.auth import permission_required

sector_bp = Blueprint('sectors', __name__, url_prefix='/sectores')


@sector_bp.route('/nuevo', methods=['GET', 'POST'])
@permission_required('sector_create')
def create():
    errors = {}
    data = {'nombre': '', 'descripcion': ''}

    if request.method == 'POST':
        data['nombre'] = request.form.get('nombre', '').strip()
        data['descripcion'] = request.form.get('descripcion', '').strip()

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
                create_sector(
                    nombre=data['nombre'],
                    descripcion=data['descripcion'],
                )
                flash('El sector fue creado exitosamente.', 'success')
                #return redirect(url_for('sectors.index'))

            except SectorAlreadyExistsError as err:
                errors['nombre'] = str(err)

            except SectorValidationError as err:
                flash(str(err), 'error')

            except Exception:
                flash('Ocurrió un error inesperado al procesar la solicitud.', 'error')

    return render_template('sectors/sector_create.html', data=data, errors=errors)