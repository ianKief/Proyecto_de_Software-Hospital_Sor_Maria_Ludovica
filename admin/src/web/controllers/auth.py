"""Controlador de autenticación y activación de cuenta para la aplicación privada."""
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from src.core.auth import autenticar_usuario
from src.core.users import obtener_usuario, actualizar_contrasena
from src.core.tokens import (
    generar_token_magic_login,
    verificar_token_magic_login,
    verificar_token_activacion,
)
from src.core.email import enviar_email_magic_login
from src.web.helpers.auth import es_administrador

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _iniciar_sesion_admin(user):
    """Inicializa la sesión de Flask con los datos del administrador recién autenticado.

    Guarda email, nombre del rol, ID del usuario y la hora actual para el control de inactividad.
    """
    session["user"] = user.email
    session["role"] = user.role.name
    session["user_id"] = user.id
    session["last_activity"] = datetime.now(timezone.utc).isoformat()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Muestra y procesa el formulario de inicio de sesión del panel privado.

    Valida email y contraseña, y verifica además que el usuario tenga rol Administrador.
    Los usuarios con roles operativos son rechazados aquí porque ingresan por el portal público.
    """
    if session.get("user"):
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password")

        if not email or not password:
            flash("Debe completar todos los campos obligatorios.", "error")
            return render_template("auth/login.html", email=email)

        user, error = autenticar_usuario(email, password)

        if error == "desactivado":
            flash("El usuario se encuentra desactivado.", "error")
            return render_template("auth/login.html", email=email)
        elif error:
            flash("Correo electrónico o contraseña incorrectos.", "error")
            return render_template("auth/login.html", email=email)

        # El panel de administración es de uso exclusivo para el rol Administrador;
        # los roles operativos ingresan desde la aplicación pública (portal).
        if not es_administrador(user):
            flash(
                "El acceso al panel de administración es exclusivo para usuarios con rol Administrador.",
                "error",
            )
            return render_template("auth/login.html", email=email)

        _iniciar_sesion_admin(user)
        flash("Sesión iniciada con éxito.", "success")
        return redirect(url_for("main.home"))

    return render_template("auth/login.html")


@auth_bp.route("/magic-login-request", methods=["POST"])
def magic_login_request():
    """Recibe un correo electrónico y envía un enlace temporal de acceso si es Administrador.

    Siempre muestra el mismo mensaje informativo para no revelar qué correos existen en la base.
    """
    email = request.form.get("email", "").strip()

    if not email:
        flash("Por favor, ingresá tu correo electrónico.", "error")
        return redirect(url_for("auth.login"))

    user = obtener_usuario(email=email)

    # Solo se envía el enlace de acceso al panel privado si es un Administrador activo
    if es_administrador(user):
        token = generar_token_magic_login(user.id)
        url_login = url_for("auth.magic_login", token=token, _external=True)
        enviar_email_magic_login(user, url_login)

    flash(
        "Si el correo electrónico corresponde a una cuenta habilitada, recibirás un enlace de acceso en tu bandeja de entrada.",
        "info",
    )
    return redirect(url_for("auth.login"))


@auth_bp.route("/magic-login")
def magic_login():
    """Procesa el clic en el enlace mágico recibido por correo e inicia la sesión del Administrador."""
    token = request.args.get("token")

    if not token:
        flash("Enlace de acceso inválido.", "error")
        return redirect(url_for("auth.login"))

    user_id = verificar_token_magic_login(token)
    if not user_id:
        flash(
            "El enlace de acceso es inválido o ha expirado. Por favor, solicitá uno nuevo.",
            "error",
        )
        return redirect(url_for("auth.login"))

    user = obtener_usuario(id=user_id)
    if not user or not user.activo:
        flash("La cuenta no se encuentra activa o no existe.", "error")
        return redirect(url_for("auth.login"))

    if not es_administrador(user):
        flash(
            "El acceso al panel de administración es exclusivo para usuarios con rol Administrador.",
            "error",
        )
        return redirect(url_for("auth.login"))

    _iniciar_sesion_admin(user)
    flash("Sesión iniciada con éxito mediante enlace de correo.", "success")
    return redirect(url_for("main.home"))


@auth_bp.route("/set-password", methods=["GET", "POST"])
def set_password():
    """Permite a un usuario nuevo activar su cuenta definiendo su contraseña por primera vez.

    Se accede desde el enlace enviado por correo al dar de alta un usuario. Una vez guardada
    la contraseña, si el usuario es Administrador entra directo al panel; si tiene un rol
    operativo, su cuenta queda activa para usarse en la aplicación pública.
    """
    token = request.args.get("token") or request.form.get("token")

    if not token:
        flash("Enlace de activación no provisto.", "error")
        return redirect(url_for("auth.login"))

    user_id = verificar_token_activacion(token)
    if not user_id:
        flash(
            "El enlace de activación es inválido o ha expirado (validez: 24 hs). Contactá al administrador.",
            "error",
        )
        return redirect(url_for("auth.login"))

    user = obtener_usuario(id=user_id)
    if not user:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for("auth.login"))

    # Si el usuario aún no está activo, es_administrador(user) devolvería False,
    # por lo que verificamos el nombre del rol directamente.
    if not (user.role and user.role.name == "Administrador"):
        portal_base = (current_app.config.get("PORTAL_URL") or "http://localhost:5173").rstrip("/")
        return redirect(f"{portal_base}/activar-cuenta?token={token}")

    if request.method == "POST":
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")

        if not password or not password_confirm:
            flash("Por favor completá ambos campos de contraseña.", "error")
            return render_template("auth/set_password.html", token=token, user=user)

        if password != password_confirm:
            flash("Las contraseñas ingresadas no coinciden.", "error")
            return render_template("auth/set_password.html", token=token, user=user)

        try:
            actualizar_contrasena(user, password)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("auth/set_password.html", token=token, user=user)

        if es_administrador(user):
            _iniciar_sesion_admin(user)
            flash("¡Tu cuenta fue activada y tu contraseña configurada con éxito!", "success")
            return redirect(url_for("main.home"))

        flash(
            "¡Tu cuenta fue activada y tu contraseña configurada con éxito! Ya podés iniciar sesión desde el portal.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/set_password.html", token=token, user=user)


@auth_bp.route("/logout")
def logout():
    """Limpia los datos de la sesión actual del Administrador y vuelve a la pantalla de login."""
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("auth.login"))
