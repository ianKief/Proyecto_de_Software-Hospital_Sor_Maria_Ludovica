from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from src.core.users.models import User
from src.core.auth.models import Role
from src.core.sectors.models import Sector
from src.web.helpers.auth import permission_required, login_required
from src.core.paginacion import paginar
from src.web.helpers.paginacion import validar_pagina
from src.core.users import (
    buscar_usuarios,
    crear_usuario,
    actualizar_usuario,
    actualizar_perfil_usuario,
    bloquear_usuario,
    desbloquear_usuario,
    eliminar_usuario_fisicamente,
    existe_usuario_con_email,
    existe_usuario_con_dni,
    assign_role,
    get_all_roles
)
from src.core.tokens import generar_token_activacion
from src.core.email import enviar_email_activacion
from src.core.users.exceptions import UserNotFoundError, RoleNotFoundError

users_bp = Blueprint('users', __name__, url_prefix='/users')


def _render_user_create(form_data=None):
    roles = Role.query.all()
    sectors = Sector.query.filter_by(activo=True).all()
    return render_template(
        'users/user_create.html',
        roles=roles,
        sectors=sectors,
        form_data=form_data or {}
    )


def _render_user_edit(user, form_data=None):
    roles = Role.query.all()
    sectors = Sector.query.filter_by(activo=True).all()
    return render_template(
        'users/user_edit.html',
        user=user,
        roles=roles,
        sectors=sectors,
        form_data=form_data
    )


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


@users_bp.route('/perfil', methods=['GET'])
@login_required
def profile_show():
    """Muestra el perfil del usuario actualmente autenticado."""
    user = User.query.get_or_404(session.get('user_id'))
    return render_template('users/profile_show.html', user=user)


@users_bp.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
def profile_edit():
    """Permite a cualquier usuario autenticado editar sus propios datos personales y contraseña."""
    user = User.query.get_or_404(session.get('user_id'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        nombre = (request.form.get('nombre') or '').strip()
        apellido = (request.form.get('apellido') or '').strip()
        dni = (request.form.get('dni') or '').strip()
        password = request.form.get('password') or ''
        password_confirm = request.form.get('password_confirm') or ''

        form_data = {
            'email': email,
            'nombre': nombre,
            'apellido': apellido,
            'dni': dni,
        }

        if not email or not nombre or not apellido or not dni:
            flash("Nombre, apellido, correo electrónico y DNI son obligatorios.", "error")
            return render_template('users/profile_edit.html', user=user, form_data=form_data)

        if existe_usuario_con_email(email, excluir_id=user.id):
            flash("Ya existe otro usuario registrado con ese correo electrónico.", "error")
            return render_template('users/profile_edit.html', user=user, form_data=form_data)

        if existe_usuario_con_dni(dni, excluir_id=user.id):
            flash("Ya existe otro usuario registrado con ese DNI.", "error")
            return render_template('users/profile_edit.html', user=user, form_data=form_data)

        if password or password_confirm:
            if password != password_confirm:
                flash("Las contraseñas ingresadas no coinciden.", "error")
                return render_template('users/profile_edit.html', user=user, form_data=form_data)

        try:
            actualizar_perfil_usuario(
                user=user,
                email=email,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                password=password
            )
        except ValueError as e:
            flash(str(e), "error")
            return render_template('users/profile_edit.html', user=user, form_data=form_data)

        session['user'] = user.email

        flash("Perfil actualizado con éxito.", "success")
        return redirect(url_for('users.profile_show'))

    return render_template('users/profile_edit.html', user=user, form_data=None)


@users_bp.route('/nuevo', methods=['GET', 'POST'])
@permission_required('user_new')
def user_new():
    if request.method == 'POST':
        # Recuperar datos del formulario
        email = (request.form.get('email') or '').strip()
        nombre = (request.form.get('nombre') or '').strip()
        apellido = (request.form.get('apellido') or '').strip()
        dni = (request.form.get('dni') or '').strip()
        role_id = (request.form.get('role_id') or '').strip()
        sector_id = (request.form.get('sector_id') or '').strip() or None

        form_data = {
            'email': email,
            'nombre': nombre,
            'apellido': apellido,
            'dni': dni,
            'role_id': int(role_id) if role_id.isdigit() else '',
            'sector_id': int(sector_id) if sector_id and sector_id.isdigit() else '',
        }

        if not email or not nombre or not apellido or not dni or not role_id:
            flash("Todos los campos obligatorios deben completarse.", "error")
            return _render_user_create(form_data)
            
        role = Role.query.get(int(role_id)) if role_id.isdigit() else None
        if not role:
            flash("El rol seleccionado no es válido.", "error")
            form_data['role_id'] = ''
            return _render_user_create(form_data)

        if role.name == "Jefe de Servicio":
            if sector_id:
                sector = Sector.query.get(int(sector_id)) if str(sector_id).isdigit() else None
                if not sector or not sector.activo:
                    flash("No se puede asociar un usuario a un sector inactivo o inexistente.", "error")
                    form_data['sector_id'] = ''
                    return _render_user_create(form_data)
                sector_id = sector.id
        else:
            sector_id = None
            form_data['sector_id'] = ''
            
        if existe_usuario_con_email(email):
            flash("Ya existe un usuario registrado con ese correo electrónico.", "error")
            return _render_user_create(form_data)

        if existe_usuario_con_dni(dni):
            flash("Ya existe un usuario registrado con ese DNI.", "error")
            return _render_user_create(form_data)

        # El usuario se crea siempre inactivo: su cuenta se activa cuando
        # configura su contraseña a través del enlace de activación enviado por email.
        nuevo_usuario = crear_usuario(
            email=email,
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            role_id=role.id,
            sector_id=sector_id,
            activo=False
        )

        # Generar token y enviar correo de activación
        token = generar_token_activacion(nuevo_usuario.id)
        url_activacion = url_for('auth.set_password', token=token, _external=True)
        enviar_email_activacion(nuevo_usuario, url_activacion)

        flash(f"Usuario {nuevo_usuario.nombre} {nuevo_usuario.apellido} creado con éxito. Se ha enviado un correo a {nuevo_usuario.email} para que active su cuenta y configure su contraseña.", "success")
        return redirect(url_for('users.user_index'))

    # Para peticiones GET
    return _render_user_create()


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
        # Recuperar datos (el administrador no puede modificar la contraseña de un usuario desde aquí)
        email = (request.form.get('email') or '').strip()
        nombre = (request.form.get('nombre') or '').strip()
        apellido = (request.form.get('apellido') or '').strip()
        dni = (request.form.get('dni') or '').strip()
        role_id = (request.form.get('role_id') or '').strip()
        sector_id = (request.form.get('sector_id') or '').strip() or None
        activo = request.form.get('activo') == 'on'

        form_data = {
            'email': email,
            'nombre': nombre,
            'apellido': apellido,
            'dni': dni,
            'role_id': int(role_id) if role_id.isdigit() else '',
            'sector_id': int(sector_id) if sector_id and sector_id.isdigit() else '',
            'activo': activo,
        }

        # Validaciones de campos obligatorios
        if not email or not nombre or not apellido or not dni or not role_id:
            flash("Todos los campos obligatorios deben completarse.", "error")
            return _render_user_edit(user, form_data)

        role = Role.query.get(int(role_id)) if role_id.isdigit() else None
        if not role:
            flash("El rol seleccionado no es válido.", "error")
            form_data['role_id'] = ''
            return _render_user_edit(user, form_data)

        if role.name == "Jefe de Servicio":
            if sector_id:
                sector = Sector.query.get(int(sector_id)) if str(sector_id).isdigit() else None
                if not sector or not sector.activo:
                    flash("No se puede asociar un usuario a un sector inactivo o inexistente.", "error")
                    form_data['sector_id'] = ''
                    return _render_user_edit(user, form_data)
                sector_id = sector.id
        else:
            # Los usuarios que no sean Jefe de Servicio no tendrán sector asociado
            sector_id = None
            form_data['sector_id'] = ''

        # Un usuario con rol Administrador no puede ser bloqueado
        if role.name == "Administrador" and not activo:
            flash("Los usuarios con rol Administrador no pueden ser bloqueados.", "error")
            form_data['activo'] = True
            return _render_user_edit(user, form_data)

        if existe_usuario_con_email(email, excluir_id=id):
            flash("Ya existe otro usuario registrado con ese correo electrónico.", "error")
            return _render_user_edit(user, form_data)
            
        if existe_usuario_con_dni(dni, excluir_id=id):
            flash("Ya existe otro usuario registrado con ese DNI.", "error")
            return _render_user_edit(user, form_data)

        try:
            actualizar_usuario(
                user=user,
                email=email,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                role_id=role.id,
                sector_id=sector_id,
                activo=activo
            )
        except ValueError as e:
            flash(str(e), "error")
            return _render_user_edit(user, form_data)

        if session.get('user_id') == user.id:
            session['user'] = user.email

        flash("Usuario actualizado con éxito.", "success")
        return redirect(url_for('users.user_show', id=id))

    return _render_user_edit(user)


@users_bp.route('/<int:id>/bloquear', methods=['POST'])
@permission_required('user_block')
def user_block(id):
    user = User.query.get_or_404(id)
    try:
        bloquear_usuario(user)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for('users.user_index'))

    flash(f"El usuario {user.nombre} {user.apellido} ha sido bloqueado exitosamente.", "success")
    return redirect(url_for('users.user_index'))


@users_bp.route('/<int:id>/desbloquear', methods=['POST'])
@permission_required('user_unblock')
def user_unblock(id):
    user = User.query.get_or_404(id)
    desbloquear_usuario(user)
    flash(f"El usuario {user.nombre} {user.apellido} ha sido desbloqueado exitosamente.", "success")
    return redirect(url_for('users.user_index'))


@users_bp.route('/<int:id>/eliminar_fisicamente', methods=['POST'])
@permission_required('user_destroy')
def user_delete_physical(id):
    user = User.query.get_or_404(id)
    try:
        eliminar_usuario_fisicamente(user)
        flash("El usuario fue eliminado permanentemente del sistema.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception:
        flash("No se pudo eliminar el usuario permanentemente.", "error")

    return redirect(url_for('users.user_index'))


@users_bp.route('/<int:id>/rol', methods=['POST'])
@permission_required('user_update')
def change_role(id):
    role_id = request.form.get('role_id', type=int)
    
    if not role_id:
        flash("Debe seleccionar un rol válido.", "error")
        return user_index(), 400 

    try:
        usuario_actualizado = assign_role(id, role_id)
        flash("Rol actualizado correctamente.", "success")
        return redirect(url_for('users.user_index'))
        
    except (UserNotFoundError, RoleNotFoundError) as e:
        flash(str(e), "error")
        return user_index(), 400

