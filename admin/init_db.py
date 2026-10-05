import os
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role, Permission
from src.core.users.models import User
from src.core.sectors.models import Sector
from src.core.personnel_types.models import PersonnelType
from src.core.menu_types.models import MenuType
from src.core.personnel.models import Personal
from src.core.food_types.models import FoodType
from src.core.quotas.models import Cupo
from src.core.pedidos.models import Pedido, SolicitudPedido, Autorizacion
import bcrypt


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
        print("Cargando sectores...")
        sector = Sector.query.filter_by(nombre="Pediatría").first()

        if not sector:
            sector = Sector(
                nombre="Pediatría",
                descripcion="Sector de prueba para desarrollo",
                activo=True,
            )
            db.session.add(sector)
            db.session.commit()

        print("Cargando tipos de personal...")
        tipos_personal = [
            "Personal Fijo",
            "Residente",
        ]

        for nombre in tipos_personal:
            if not PersonnelType.query.filter_by(nombre=nombre).first():
                db.session.add(PersonnelType(nombre=nombre))

        print("Cargando tipos de menú...")
        tipos_menu = [
            "General",
            "Vegetariano",
            "Celiaco",
        ]

        for nombre in tipos_menu:
            if not MenuType.query.filter_by(nombre=nombre).first():
                db.session.add(MenuType(nombre=nombre))

        db.session.commit()

        print("Cargando tipos de comida...")
        tipos_comida = [
            "Desayuno",
            "Almuerzo",
            "Merienda",
            "Cena",
        ]

        for nombre in tipos_comida:
            if not FoodType.query.filter_by(nombre=nombre).first():
                db.session.add(FoodType(nombre=nombre))

        db.session.commit()
        print("Cargando cupos de prueba...")

        tipos_comida_db = {
            "Desayuno": FoodType.query.filter_by(nombre="Desayuno").first(),
            "Almuerzo": FoodType.query.filter_by(nombre="Almuerzo").first(),
            "Merienda": FoodType.query.filter_by(nombre="Merienda").first(),
            "Cena": FoodType.query.filter_by(nombre="Cena").first(),
        }

        for nombre_comida, tipo_comida in tipos_comida_db.items():
            if not Cupo.query.filter_by(
                sector_id=sector.id,
                tipo_comida_id=tipo_comida.id,
            ).first():
                db.session.add(
                    Cupo(
                        sector_id=sector.id,
                        tipo_comida_id=tipo_comida.id,
                        cantidad=1,
                    )
                )

        db.session.commit()
        print("Cargando personal de prueba...")

        tipo_fijo = PersonnelType.query.filter_by(
            nombre="Personal Fijo"
        ).first()

        tipo_residente = PersonnelType.query.filter_by(
            nombre="Residente"
        ).first()

        menu_general = MenuType.query.filter_by(
            nombre="General"
        ).first()

        menu_celiaco = MenuType.query.filter_by(
            nombre="Celiaco"
        ).first()

        if not Personal.query.filter_by(dni="30111222").first():
            db.session.add(
                Personal(
                    dni="30111222",
                    nombre="Ana",
                    apellido="Gómez",
                    personnel_type_id=tipo_fijo.id,
                    sector_id=sector.id,
                    menu_type_id=menu_general.id,
                    activo=True,
                )
            )

        if not Personal.query.filter_by(dni="30999888").first():
            db.session.add(
                Personal(
                    dni="30999888",
                    nombre="Lucía",
                    apellido="Fernández",
                    personnel_type_id=tipo_residente.id,
                    sector_id=None,
                    menu_type_id=menu_celiaco.id,
                    activo=True,
                )
            )

        db.session.commit()
        print("Cargando roles base...")
        roles = ["Administrador", "Jefe de Servicio", "Servicio de Alimentación", "Sector Comedor"]
        for role_name in roles:
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name))
        
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
