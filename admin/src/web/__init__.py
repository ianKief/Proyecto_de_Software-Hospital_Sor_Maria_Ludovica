from flask import Flask
from src.web.handlers.error import register_error_handlers
from web.routes import bp
import os

def _get_static_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    admin_dir = os.path.dirname(os.path.dirname(base_dir))
    return os.path.join(admin_dir, "static")

def create_app(env="development", static_folder=None):
    if static_folder == None:
        static_folder = _get_static_path()

    app = Flask(__name__, static_folder=static_folder)
    app.register_blueprint(bp)

    register_error_handlers(app)
    return app