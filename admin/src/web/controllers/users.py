from flask import Blueprint, render_template, request, flash, redirect, url_for
from src.core.users.models import User
from src.core.auth.models import Role
from src.web.helpers.auth import permission_required
from src.core.db import db
import bcrypt

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@permission_required('user_index')
def user_index():
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=25, error_out=False)
    return render_template('users/users_list.html', users=users)

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
        activo = request.form.get('activo') == 'on' # El checkbox devuelve 'on' si está marcado

        # Validaciones de servidor (Requeridas por PDF)
        if not email or not nombre or not apellido or not dni or not password or not role_id:
            flash("Todos los campos obligatorios deben completarse.", "error")
            return redirect(url_for('users.user_new'))

        if User.query.filter_by(email=email).first():
            flash("Ya existe un usuario registrado con ese correo electrónico.", "error")
            return redirect(url_for('users.user_new'))

        if User.query.filter_by(dni=dni).first():
            flash("Ya existe un usuario registrado con ese DNI.", "error")
            return redirect(url_for('users.user_new'))

        # Manejo seguro de contraseñas
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        new_user = User(
            email=email,
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            password=hashed_password,
            activo=activo,
            role_id=role_id
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Usuario creado con éxito.", "success")
        return redirect(url_for('users.user_index'))

    # Para peticiones GET, buscamos los roles en la BD para el desplegable
    roles = Role.query.all()
    return render_template('users/user_create.html', roles=roles)
