from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from src.core.auth import autenticar_usuario

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user'):
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Debe completar todos los campos obligatorios.", "error")
            return render_template('auth/login.html')

        user, error = autenticar_usuario(email, password)

        if error == "desactivado":
            flash("El usuario se encuentra desactivado.", "error")
            return render_template('auth/login.html')
        elif error:
            flash("Correo electrónico o contraseña incorrectos.", "error")
            return render_template('auth/login.html')

        session['user'] = user.email
        session['role'] = user.role.name
        session['user_id'] = user.id
        flash("Sesión iniciada con éxito.", "success")
        return redirect(url_for('main.home'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('auth.login'))
