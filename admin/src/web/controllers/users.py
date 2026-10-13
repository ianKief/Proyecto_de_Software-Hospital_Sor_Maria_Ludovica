from flask import Blueprint, render_template, request, flash, redirect, url_for
from src.core.users.models import User
from src.core.auth.models import Role
from src.core.sectors.models import Sector
from src.web.helpers.auth import permission_required
from src.core.paginacion import paginar
from src.web.helpers.paginacion import validar_pagina
from src.core.users import (
    buscar_usuarios,
    crear_usuario,
    actualizar_usuario,
    dar_de_baja_usuario,
    reactivar_usuario,
    existe_usuario_con_email,
    existe_usuario_con_dni,
)

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@permission_required('user_index')
def user_index():
    numero = validar_pagina(request.args.get('page')) or 1
    email = request.args.get('email', '').strip()
    nombre_apellido = request.args.get('nombre_apellido', '').strip()
    dni = request.args.get('dni', '').strip()
    activo = request.args.get('activo', '').strip()
    role_id = request.args.get('role_id', '').strip()
    sector_id = request.args.get('sector_id', '').strip()
    order_by = request.args.get('order_by', 'created_at').strip()
    order_dir = request.args.get('order_dir', 'desc').strip()

    query = buscar_usuarios(
        email=email,
        nombre_apellido=nombre_apellido,
        dni=dni,
        activo=activo,
        role_id=role_id,
        sector_id=sector_id,
        order_by=order_by,
        order_dir=order_dir
    )

    users = paginar(query, numero)
    roles = Role.query.all()
    sectors = Sector.query.all()

    filters = {
        'email': email,
        'nombre_apellido': nombre_apellido,
        'dni': dni,
        'activo': activo,
        'role_id': int(role_id) if role_id.isdigit() else '',
        'sector_id': int(sector_id) if sector_id.isdigit() else '',
        'order_by': order_by,
        'order_dir': order_dir
    }

    return render_template(
        'users/users_list.html',
        users=users,
        roles=roles,
        sectors=sectors,
        filters=filters
    )

@users_bp.route('/nuevo', methods=['GET', 'POST'])
@permission_required('user_new')
def user_new():
    if request.method == 'POST':
        # Recuperar datos del formulario
        email = request.form.get('email')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        dni = request.form.get('dni')
        password = request.form.get('password')
        role_id = request.form.get('role_id')
        sector_id = request.form.get('sector_id') or None
        activo = request.form.get('activo') == 'on'

        if not email or not nombre or not apellido or not dni or not password or not role_id:
            flash("Todos los campos obligatorios deben completarse.", "error")
            return redirect(url_for('users.user_new'))
            
        role = Role.query.get(role_id)
        if role and role.name == "Jefe de Servicio":
            if not sector_id:
                flash("El Sector es obligatorio para usuarios con rol 'Jefe de Servicio'.", "error")
                return redirect(url_for('users.user_new'))
            sector = Sector.query.get(sector_id)
            if not sector or not sector.activo:
                flash("No se puede asociar un usuario a un sector inactivo o inexistente.", "error")
                return redirect(url_for('users.user_new'))
        else:
            sector_id = None
            
        if existe_usuario_con_email(email):
            flash("Ya existe un usuario registrado con ese correo electrónico.", "error")
            return redirect(url_for('users.user_new'))

        if existe_usuario_con_dni(dni):
            flash("Ya existe un usuario registrado con ese DNI.", "error")
            return redirect(url_for('users.user_new'))

        crear_usuario(
            email=email,
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            password=password,
            role_id=role_id,
            sector_id=sector_id,
            activo=activo
        )

        flash("Usuario creado con éxito.", "success")
        return redirect(url_for('users.user_index'))

    # Para peticiones GET
    roles = Role.query.all()
    sectors = Sector.query.all()
    return render_template('users/user_create.html', roles=roles, sectors=sectors)

@users_bp.route('/<int:id>')
@permission_required('user_show')
def user_show(id):
    user = User.query.get_or_404(id)
    return render_template('users/user_show.html', user=user)

@users_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@permission_required('user_update')
def user_update(id):
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        # Recuperar datos
        email = request.form.get('email')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        dni = request.form.get('dni')
        password = request.form.get('password')
        role_id = request.form.get('role_id')
        sector_id = request.form.get('sector_id') or None
        activo = request.form.get('activo') == 'on'

        # Validaciones de campos obligatorios (la password puede venir vacía si no se quiere cambiar)
        if not email or not nombre or not apellido or not dni or not role_id:
            flash("Todos los campos excepto la contraseña son obligatorios.", "error")
            return redirect(url_for('users.user_update', id=id))

        role = Role.query.get(role_id)
        if role and role.name == "Jefe de Servicio":
            if not sector_id:
                flash("El Sector es obligatorio para usuarios con rol 'Jefe de Servicio'.", "error")
                return redirect(url_for('users.user_update', id=id))
            sector = Sector.query.get(sector_id)
            if not sector or not sector.activo:
                flash("No se puede asociar un usuario a un sector inactivo o inexistente.", "error")
                return redirect(url_for('users.user_update', id=id))
        else:
            # Los usuarios que no sean Jefe de Servicio no tendrán sector asociado
            sector_id = None

        # Un usuario con rol Administrador no puede ser bloqueado
        if role and role.name == "Administrador" and not activo:
            flash("Los usuarios con rol Administrador no pueden ser bloqueados.", "error")
            return redirect(url_for('users.user_update', id=id))

        if existe_usuario_con_email(email, excluir_id=id):
            flash("Ya existe otro usuario registrado con ese correo electrónico.", "error")
            return redirect(url_for('users.user_update', id=id))
            
        if existe_usuario_con_dni(dni, excluir_id=id):
            flash("Ya existe otro usuario registrado con ese DNI.", "error")
            return redirect(url_for('users.user_update', id=id))

        try:
            actualizar_usuario(
                user=user,
                email=email,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                role_id=role_id,
                sector_id=sector_id,
                activo=activo,
                password=password
            )
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for('users.user_update', id=id))

        flash("Usuario actualizado con éxito.", "success")
        return redirect(url_for('users.user_show', id=id))

    roles = Role.query.all()
    sectors = Sector.query.all()
    return render_template('users/user_edit.html', user=user, roles=roles, sectors=sectors)

@users_bp.route('/<int:id>/eliminar', methods=['POST'])
@permission_required('user_destroy')
def user_destroy(id):
    user = User.query.get_or_404(id)
    try:
        dar_de_baja_usuario(user)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for('users.user_index'))

    flash(f"El usuario {user.nombre} {user.apellido} ha sido dado de baja exitosamente.", "success")
    return redirect(url_for('users.user_index'))

@users_bp.route('/<int:id>/activar', methods=['POST'])
@permission_required('user_update')
def user_activate(id):
    user = User.query.get_or_404(id)
    reactivar_usuario(user)
    flash(f"El usuario {user.nombre} {user.apellido} ha sido reactivado exitosamente.", "success")
    return redirect(url_for('users.user_index'))
