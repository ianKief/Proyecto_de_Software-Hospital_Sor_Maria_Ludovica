import os
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role, Permission
from src.core.users.models import User
import bcrypt
from src.core.sectors.models import Sector
from src.core.personnel.models import PersonnelType, MenuType, Personnel
from src.core.quotas.models import Quota

def ensure_database_exists(db_url):
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip('/')
    
    # Connect to the default "postgres" database to create our new DB
    conn_url = db_url.replace(f"/{db_name}", "/postgres")
    
    # Use SQLAlchemy to create DB (bypass psycopg2 driver limitations using pg8000)
    engine = create_engine(conn_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        # Check if database exists
        result = conn.execute(text(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'"))
        exists = result.fetchone()
        if not exists:
            print(f"La base de datos '{db_name}' no existe. Creándola...")
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            print("Base de datos creada exitosamente.")
        else:
            print(f"La base de datos '{db_name}' ya existe.")

if __name__ == '__main__':
    app = create_app()
    
    db_url = app.config.get("SQLALCHEMY_DATABASE_URI")
    ensure_database_exists(db_url)

    with app.app_context():
        print("Creando tablas...")
        db.create_all()

        print("Cargando roles base...")
        roles = ["Administrador", "Jefe de Servicio", "Servicio de Alimentación", "Sector Comedor"]
        for role_name in roles:
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name))

        print("Cargando tipos de personal base...")
        personnel_types = ["Personal Fijo", "Residente", "Eventual"]
        for pt_name in personnel_types:
            if not PersonnelType.query.filter_by(nombre=pt_name).first():
                db.session.add(PersonnelType(nombre=pt_name))

        print("Cargando tipos de menú base...")
        menu_types = ["General", "Vegetariano", "Celiaco"]
        for mt_name in menu_types:
            if not MenuType.query.filter_by(nombre=mt_name).first():
                db.session.add(MenuType(nombre=mt_name))
        
        db.session.commit()

        print("Creando usuario administrador...")
        admin_role = Role.query.filter_by(name="Administrador").first()
        if not User.query.filter_by(email="admin@hospital.com").first():
            hashed_password = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode('utf-8')
            admin = User(
                email="admin@hospital.com",
                nombre="Admin",
                apellido="Sistema",
                dni="00000000",
                password=hashed_password,
                activo=True,
                role_id=admin_role.id
            )
            db.session.add(admin)
            db.session.commit()
            print("Administrador creado exitosamente:")
            print("  Email: admin@hospital.com")
            print("  Pass : admin123")
        else:
            print("El administrador ya estaba creado.")
