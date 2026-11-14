import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')
    TESTING = False
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # Duración del token JWT de la API (en horas, pensado para cubrir un turno completo)
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', 12))

    # Orígenes permitidos para peticiones CORS desde la aplicación pública (separados por coma)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')

    # Configuración de Correo (Flask-Mail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() in ['true', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', None)
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', None)
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@hospital.com')


class DevelopmentConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    pass


class TestingConfig(Config):
    TESTING = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
