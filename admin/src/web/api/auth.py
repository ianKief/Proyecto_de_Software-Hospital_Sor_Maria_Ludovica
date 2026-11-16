"""Endpoints de autenticación y gestión de perfil para la aplicación pública (portal)."""
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from flask import Blueprint, request, jsonify, current_app

from src.core.users.models import User
from src.core.users import (
    actualizar_perfil_usuario,
    existe_usuario_con_email,
    existe_usuario_con_dni,
)
from src.web.helpers.api_auth import token_required
from src.web.helpers.auth_validaciones import (
    es_rol_operativo_portal,
    validar_datos_login_api,
    validar_datos_google_login_api,
    verificar_id_token_google,
    validar_acceso_usuario_portal,
    validar_datos_perfil_api,
)

api_auth_bp = Blueprint("api_auth", __name__, url_prefix="/api/auth")


def _serializar_usuario(user):
    """Arma el diccionario con los datos públicos del usuario autenticado.

    Incluye su identificador, datos personales, nombre del rol y sector asociado
    para que el frontend pueda configurar la sesión y el menú sin exponer hashes.
    """
    return {
        "id": user.id,
        "nombre": user.nombre,
        "apellido": user.apellido,
        "email": user.email,
        "dni": user.dni,
        "rol": user.role.name if user.role else None,
        "sector": user.sector.nombre if user.sector else None,
        "sector_id": user.sector_id,
    }


def _generar_token_acceso(user):
    """Emite un token JWT firmado con una duración pensada para cubrir un turno completo.

    Guarda el ID del usuario en el claim ``sub`` y calcula la fecha de vencimiento (``exp``)
    según la variable ``JWT_EXPIRATION_HOURS`` definida en la configuración.
    """
    horas_expiracion = current_app.config.get("JWT_EXPIRATION_HOURS", 12)
    payload = {
        "sub": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=horas_expiracion),
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


@api_auth_bp.route("/login", methods=["POST"])
def login():
    """Autentica a un usuario operativo con email y contraseña y devuelve un token JWT.

    Flujo:
    1. Valida el formato del JSON de entrada (400 si faltan datos o el email es inválido).
    2. Verifica que el usuario exista y que la contraseña coincida con su hash bcrypt (401 si falla).
    3. Comprueba que la cuenta esté activa y tenga un rol operativo del portal (403 si es
       Administrador o está bloqueado).
    4. Devuelve el token JWT junto con los datos del usuario (200).
    """
    data = request.get_json(silent=True)
    datos, error_validacion = validar_datos_login_api(data)
    if error_validacion:
        return jsonify({"error": error_validacion}), 400

    user = User.query.filter_by(email=datos["email"]).first()
    if not user:
        return jsonify({"error": "Credenciales inválidas"}), 401

    try:
        valido = bcrypt.checkpw(
            datos["password"].encode("utf-8"),
            user.password.encode("utf-8"),
        )
    except Exception:
        valido = False

    if not valido:
        return jsonify({"error": "Credenciales inválidas"}), 401

    # Una vez verificadas las credenciales, comprobamos que la cuenta esté activa
    # y que su rol corresponda a uno de los roles operativos del portal.
    error_acceso, status_code = validar_acceso_usuario_portal(user)
    if error_acceso:
        return jsonify({"error": error_acceso}), status_code

    token = _generar_token_acceso(user)
    return jsonify({
        "token": token,
        "user": _serializar_usuario(user),
    }), 200


@api_auth_bp.route("/google", methods=["POST"])
def login_google():
    """Autentica a un usuario operativo validando el ID token de Google Identity Services.

    Flujo:
    1. Verifica que se haya enviado el campo ``id_token`` en el cuerpo JSON (400 si falta).
    2. Valida firma, emisor, audiencia (``GOOGLE_CLIENT_ID``) y expiración del token (401 si es inválido).
    3. Busca el correo verificado en la base de datos local sin crear usuarios nuevos (403 si no existe,
       está bloqueado o tiene rol Administrador).
    4. Devuelve el mismo formato de token JWT y datos de usuario que el login tradicional (200).
    """
    data = request.get_json(silent=True)
    token_google, error_datos = validar_datos_google_login_api(data)
    if error_datos:
        return jsonify({"error": error_datos}), 400

    client_id = current_app.config.get("GOOGLE_CLIENT_ID", "")
    email_verificado, error_token = verificar_id_token_google(token_google, client_id)
    if error_token:
        return jsonify({"error": error_token}), 401

    # El inicio de sesión con Google no da de alta cuentas automáticamente:
    # el correo debe pertenecer a un usuario previamente registrado por el Administrador.
    user = User.query.filter_by(email=email_verificado).first()
    if not user:
        return jsonify({
            "error": "No existe una cuenta registrada con ese correo electrónico. Debe solicitar el alta al Administrador."
        }), 403

    error_acceso, status_code = validar_acceso_usuario_portal(user)
    if error_acceso:
        return jsonify({"error": error_acceso}), status_code

    token = _generar_token_acceso(user)
    return jsonify({
        "token": token,
        "user": _serializar_usuario(user),
    }), 200


@api_auth_bp.route("/me", methods=["GET"])
@token_required
def me(current_user):
    """Retorna los datos del usuario autenticado a partir del token Bearer enviado en el header."""
    return jsonify(_serializar_usuario(current_user)), 200


@api_auth_bp.route("/me", methods=["PUT"])
@token_required
def update_me(current_user):
    """Permite al usuario autenticado del portal editar sus datos personales y su contraseña.

    Valida que el usuario pertenezca a uno de los roles operativos (403 si no), comprueba
    el formato de nombre, apellido, email, DNI y contraseña opcional (400 si hay errores),
    verifica que el email y DNI no estén ocupados por otro usuario (409) y persiste los cambios.
    """
    if not es_rol_operativo_portal(current_user):
        return jsonify({
            "error": "Solo los roles operativos del portal pueden editar su perfil por esta vía."
        }), 403

    data = request.get_json(silent=True)
    datos, errores_campos, error_validacion = validar_datos_perfil_api(data)
    if error_validacion:
        return jsonify({"error": error_validacion, "fields": errores_campos}), 400

    if existe_usuario_con_email(datos["email"], excluir_id=current_user.id):
        mensaje = "Ya existe otro usuario registrado con ese correo electrónico."
        return jsonify({"error": mensaje, "fields": {"email": mensaje}}), 409

    if existe_usuario_con_dni(datos["dni"], excluir_id=current_user.id):
        mensaje = "Ya existe otro usuario registrado con ese DNI."
        return jsonify({"error": mensaje, "fields": {"dni": mensaje}}), 409

    try:
        actualizar_perfil_usuario(
            user=current_user,
            email=datos["email"],
            nombre=datos["nombre"],
            apellido=datos["apellido"],
            dni=datos["dni"],
            password=datos["password"],
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "message": "Perfil actualizado correctamente.",
        "user": _serializar_usuario(current_user),
    }), 200


@api_auth_bp.route("/logout", methods=["POST"])
@token_required
def logout(current_user=None):
    """Confirma el cierre de sesión del usuario autenticado para que el cliente descarte su token."""
    return jsonify({
        "message": "Sesión cerrada correctamente"
    }), 200
