import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')
    TESTING = False
    SESSION_TYPE = 'filesystem'

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