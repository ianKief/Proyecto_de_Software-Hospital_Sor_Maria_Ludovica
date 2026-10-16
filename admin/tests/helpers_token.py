"""Helpers para autenticar los tests de la API con un token JWT.

La API ya no mira la sesión: exige el header ``Authorization: Bearer <token>``
(ver ``src/web/helpers/api_auth.py``). El token se arma igual que en
``POST /api/auth/login``, pero sin pasar por el login, porque los usuarios
de prueba no tienen una contraseña bcrypt válida.
"""
from datetime import datetime, timedelta, timezone

import jwt


def headers_con_token(app, usuario, horas=12):
    """Devuelve el header ``Authorization`` con un token para ``usuario``.

    ``horas`` es cuánto falta para que venza: con un número negativo el
    token ya está vencido (sirve para probar el 401 de token expirado).
    """
    payload = {
        "sub": usuario.id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=horas),
    }
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def cliente_con_token(app, usuario):
    """Devuelve un cliente de pruebas que manda el token de ``usuario`` en cada pedido.

    ``environ_base`` son valores que el cliente de Flask agrega a todos sus
    pedidos; ``HTTP_AUTHORIZATION`` es el nombre que usa WSGI para el header
    ``Authorization``. Así los tests siguen haciendo ``client.get(url)``
    sin repetir ``headers=...`` en cada llamada.
    """
    client = app.test_client()
    client.environ_base["HTTP_AUTHORIZATION"] = headers_con_token(app, usuario)["Authorization"]
    return client
