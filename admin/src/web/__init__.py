from flask import Flask
from flask_session import Session
from src.web.handlers.error import register_error_handlers
from src.web.controllers.routes import bp
from src.web.controllers.users import users_bp
from src.web.controllers.auth import auth_bp
from src.web.controllers.configuration import configuration_bp
from src.web.controllers.api_configuration import api_configuration_bp
from src.web.controllers.personnel import bp as personnel_bp
from src.web.helpers.auth import check_permission
from src.web.helpers.mantenimiento import verificar_mantenimiento
import logging
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
    # Muestra en la terminal los logs INFO o más graves, con fecha y hora (la spec pide registro de eventos y errores en el backend).
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

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
    app.register_blueprint(configuration_bp)
    app.register_blueprint(api_configuration_bp)
    app.register_blueprint(personnel_bp)
    app.jinja_env.globals["check_permission"] = check_permission
    app.before_request(verificar_mantenimiento)

    register_error_handlers(app)

    @app.cli.command("reset-db")
    def reset_db():
        """Destruye la base de datos, la vuelve a crear y corre los seeds."""
        db.drop_all()
        print("Tablas destruidas correctamente.")
        
        # Corremos los scripts de inicializacion existentes
        import subprocess
        import sys
        subprocess.run([sys.executable, "init_db.py"])
        subprocess.run([sys.executable, "-m", "src.core.seeds.seed_permissions"])
        print("¡Base de datos reseteada y poblada exitosamente!")

    return app