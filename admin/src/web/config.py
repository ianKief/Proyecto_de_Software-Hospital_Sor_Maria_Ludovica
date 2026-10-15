import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')
    TESTING = False
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
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