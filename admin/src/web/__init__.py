import logging
import os
from dotenv import load_dotenv
from flask import Flask
from flask_session import Session

from src.core.db import db
from src.core.email import mail
from src.web.config import config
from src.web.handlers.error import register_error_handlers
from src.web.helpers.auth import check_permission, verificar_timeout_sesion
from src.web.helpers.mantenimiento import verificar_mantenimiento

# Controladores Web
from src.web.controllers.routes import bp
from src.web.controllers.users import users_bp
from src.web.controllers.auth import auth_bp
from src.web.controllers.sectors import sector_bp
from src.web.controllers.pedidos import pedidos_bp
from src.web.controllers.authorizations import authorizations_bp
from src.web.controllers.summaries import summaries_bp
from src.web.controllers.configuration import configuration_bp
from src.web.controllers.personnel import bp as personnel_bp
from src.web.controllers.quotas import bp as quotas_bp

# Controladores API
from src.web.controllers.api_configuration import api_configuration_bp
from src.web.controllers.api_deliveries import api_deliveries_bp
from src.web.controllers.api_sector import api_sector_bp
from src.web.api.auth import api_auth_bp
from src.web.api.personnel import api_personnel_bp
from src.web.api.quotas import api_quotas_bp

session_ext = Session()


def _get_static_path():
    # Encuentra la carpeta static relativa a la raíz de admin
    current_dir = os.path.dirname(os.path.abspath(__file__))  # src/web
    admin_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # admin/
    return os.path.join(admin_dir, "static")


def create_app(env="development", static_folder=None):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if static_folder is None:
        static_folder = _get_static_path()

    app = Flask(__name__, static_folder=static_folder)

    load_dotenv()
    app.config.from_object(config[env])
    if os.environ.get("DATABASE_URL"):
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

    db.init_app(app)
    session_ext.init_app(app)
    mail.init_app(app)

    # Registro de Blueprints Web
    app.register_blueprint(bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(sector_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(authorizations_bp)
    app.register_blueprint(summaries_bp)
    app.register_blueprint(configuration_bp)
    app.register_blueprint(personnel_bp)
    app.register_blueprint(quotas_bp)

    # Registro de Blueprints API
    app.register_blueprint(api_configuration_bp)
    app.register_blueprint(api_deliveries_bp)
    app.register_blueprint(api_sector_bp)
    app.register_blueprint(api_auth_bp)
    app.register_blueprint(api_personnel_bp)
    app.register_blueprint(api_quotas_bp)

    # Helpers y Middlewares
    app.jinja_env.globals["check_permission"] = check_permission
    app.before_request(verificar_mantenimiento)
    app.before_request(verificar_timeout_sesion)

    register_error_handlers(app)

    @app.cli.command("reset-db")
    def reset_db():
        """Destruye la base de datos, la vuelve a crear y corre los seeds."""
        db.drop_all()
        print("Tablas destruidas correctamente.")

        import subprocess
        import sys
        subprocess.run([sys.executable, "init_db.py"])
        subprocess.run([sys.executable, "-m", "src.core.seeds.seed_permissions"])
        print("¡Base de datos reseteada y poblada exitosamente!")

    return app