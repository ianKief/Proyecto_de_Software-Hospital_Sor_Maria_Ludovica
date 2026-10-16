from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from flask import Blueprint, request, jsonify, current_app
from src.core.users.models import User
from src.web.helpers.api_auth import token_required

api_auth_bp = Blueprint('api_auth', __name__, url_prefix='/api/auth')


@api_auth_bp.route('/login', methods=['POST'])
def login():
    """Autentica al usuario mediante email y contraseña, retornando un token JWT."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Formato JSON inválido o faltante"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Debe proporcionar email y password"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.activo:
        return jsonify({"error": "Credenciales inválidas o usuario inactivo"}), 401

    try:
        valido = bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8'))
    except Exception:
        valido = False

    if not valido:
        return jsonify({"error": "Credenciales inválidas"}), 401

    payload = {
        "sub": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12)
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return jsonify({"token": token}), 200


@api_auth_bp.route('/me', methods=['GET'])
@token_required
def me(current_user):
    """Retorna los datos del usuario autenticado."""
    return jsonify({
        "id": current_user.id,
        "nombre": current_user.nombre,
        "apellido": current_user.apellido,
        "email": current_user.email,
        "rol": current_user.role.name if current_user.role else None,
        "sector": current_user.sector.nombre if current_user.sector else None
    }), 200


@api_auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user=None):
    """Cierra la sesión del usuario autenticado."""
    return jsonify({
        "message": "Sesión cerrada correctamente"
    }), 200
