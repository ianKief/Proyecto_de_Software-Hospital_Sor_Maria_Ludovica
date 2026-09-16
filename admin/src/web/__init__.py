from flask import Flask
from src.web.handlers.error import register_error_handlers

from web.routes import bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp)

    register_error_handlers(app)
    return app