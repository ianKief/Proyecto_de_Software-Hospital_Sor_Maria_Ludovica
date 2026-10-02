from flask import Flask
from flask_session import Session
from src.web.handlers.error import register_error_handlers
from src.web.controllers.routes import bp
from src.web.controllers.users import users_bp
from src.web.controllers.auth import auth_bp
from src.web.controllers.pedidos import pedidos_bp
import os
from .config import config
from src.core.db import db
from dotenv import load_dotenv

session_ext = Session()

def _get_static_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    admin_dir = os.path.dirname(os.path.dirname(base_dir))
    return os.path.join(admin_dir, "static")

def create_app(env="development", static_folder=None):
    if static_folder == None:
        static_folder = _get_static_path()
        
    app = Flask(__name__, static_folder=static_folder)

    app.config.from_object(config[env])

    load_dotenv()
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

    db.init_app(app)
    session_ext.init_app(app)

    # Blueprints
    app.register_blueprint(bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(pedidos_bp)

    register_error_handlers(app)
    return app