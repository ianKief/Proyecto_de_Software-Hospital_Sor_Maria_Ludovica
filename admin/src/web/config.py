""" Clases de configuración de la aplicación Flask según el entorno de ejecución."""
import os
from datetime import timedelta


class Config:
    """Configuración base compartida por todos los entornos."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "mysecretkey")
    TESTING = False
    SESSION_TYPE = "filesystem"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # Duración del token JWT de la API (en horas, pensado para cubrir un turno completo)
    JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", 12))

    # Orígenes permitidos para peticiones CORS desde la aplicación pública (separados por coma)
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    # Client ID de Google Identity Services para verificar el inicio de sesión con Google
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

    # Configuración de Correo (Flask-Mail)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "false").lower() in ["true", "1"]
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() in ["true", "1"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", None)
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", None)
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@hospital.com")


class DevelopmentConfig(Config):
    """Configuración para el entorno local de desarrollo."""

    TESTING = True


class ProductionConfig(Config):
    """Configuración para el despliegue en el servidor de producción."""

    pass


class TestingConfig(Config):
    """Configuración utilizada durante la ejecución de pruebas automatizadas."""

    TESTING = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
