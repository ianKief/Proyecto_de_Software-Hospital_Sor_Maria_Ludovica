from flask import Blueprint, render_template, request, flash, redirect, url_for
from sqlalchemy import or_
from src.core.users.models import User
from src.core.auth.models import Role
from src.core.sectors.models import Sector
from src.web.helpers.auth import permission_required
from src.core.paginacion import paginar
from src.web.helpers.paginacion import validar_pagina
from src.core.db import db
import bcrypt

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

    query = User.query

    # Filtros combinables
    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
    if nombre_apellido:
        query = query.filter(or_(User.nombre.ilike(f"%{nombre_apellido}%"), User.apellido.ilike(f"%{nombre_apellido}%")))
    if dni:
        query = query.filter(User.dni.ilike(f"%{dni}%"))
    if activo in ['true', '1']:
        query = query.filter(User.activo.is_(True))
    elif activo in ['false', '0']:
        query = query.filter(User.activo.is_(False))
    if role_id and role_id.isdigit():
        query = query.filter(User.role_id == int(role_id))
    if sector_id and sector_id.isdigit():
        query = query.filter(User.sector_id == int(sector_id))

    # Ordenamiento
    if order_by == 'email':
        order_clause = [User.email.desc() if order_dir == 'desc' else User.email.asc()]
    elif order_by == 'apellido_nombre':
        order_clause = [
            User.apellido.desc() if order_dir == 'desc' else User.apellido.asc(),
            User.nombre.desc() if order_dir == 'desc' else User.nombre.asc()
        ]
    else:
        order_by = 'created_at'
        order_clause = [User.created_at.desc() if order_dir == 'desc' else User.created_at.asc()]

    query = query.order_by(*order_clause)

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
            
        if User.query.filter_by(email=email).first():
            flash("Ya existe un usuario registrado con ese correo electrónico.", "error")
            return redirect(url_for('users.user_new'))

        if User.query.filter_by(dni=dni).first():
            flash("Ya existe un usuario registrado con ese DNI.", "error")
            return redirect(url_for('users.user_new'))

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        new_user = User(
            email=email,
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            password=hashed_password,
            activo=activo,
            role_id=role_id,
            sector_id=sector_id
        )

        db.session.add(new_user)
        db.session.commit()

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

        # Validar DNI y Email (que no pertenezcan a OTRO usuario)
        if User.query.filter(User.email == email, User.id != id).first():
            flash("Ya existe otro usuario registrado con ese correo electrónico.", "error")
            return redirect(url_for('users.user_update', id=id))
            
        if User.query.filter(User.dni == dni, User.id != id).first():
            flash("Ya existe otro usuario registrado con ese DNI.", "error")
            return redirect(url_for('users.user_update', id=id))

        # Actualizar campos
        user.email = email
        user.nombre = nombre
        user.apellido = apellido
        user.dni = dni
        user.role_id = role_id
        user.sector_id = sector_id
        user.activo = activo
        
        if password and password.strip() != "":
            user.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        db.session.commit()
        flash("Usuario actualizado con éxito.", "success")
        return redirect(url_for('users.user_show', id=id))

    roles = Role.query.all()
    sectors = Sector.query.all()
    return render_template('users/user_edit.html', user=user, roles=roles, sectors=sectors)

@users_bp.route('/<int:id>/eliminar', methods=['POST'])
@permission_required('user_destroy')
def user_destroy(id):
    user = User.query.get_or_404(id)

    # Regla: No se puede dar de baja a un Administrador
    if user.role.name == "Administrador":
        flash("Los usuarios con rol Administrador no pueden ser bloqueados ni dados de baja.", "error")
        return redirect(url_for('users.user_index'))

    # Baja lógica estricta
    user.activo = False
    db.session.commit()

    flash(f"El usuario {user.nombre} {user.apellido} ha sido dado de baja exitosamente.", "success")
    return redirect(url_for('users.user_index'))

@users_bp.route('/<int:id>/activar', methods=['POST'])
@permission_required('user_update')
def user_activate(id):
    user = User.query.get_or_404(id)
    user.activo = True
    db.session.commit()
    flash(f"El usuario {user.nombre} {user.apellido} ha sido reactivado exitosamente.", "success")
    return redirect(url_for('users.user_index'))


