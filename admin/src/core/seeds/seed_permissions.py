from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role, Permission

app = create_app()

with app.app_context():
    print("Verificando permisos...")
    permisos = ["user_index", "user_new", "user_show", "user_update", "user_destroy", "config_show", "config_update"]

    # Crear permisos si no existen
    for p_name in permisos:
        perm = Permission.query.filter_by(name=p_name).first()
        if not perm:
            perm = Permission(name=p_name)
            db.session.add(perm)

    db.session.commit()

    # Asignar permisos al Administrador
    admin_role = Role.query.filter_by(name="Administrador").first()
    if admin_role:
        for p_name in permisos:
            perm = Permission.query.filter_by(name=p_name).first()
            if perm not in admin_role.permissions:
                admin_role.permissions.append(perm)
        db.session.commit()
        print("Permisos cargados y asignados al rol Administrador con éxito.")
    else:
        print("No se encontró el rol Administrador.")

    # Permisos de Entregas: el Sector Comedor registra y consulta,
    # el Servicio de Alimentación solo consulta.
    permisos_por_rol = {
        "Sector Comedor": ["delivery_index", "delivery_show", "delivery_new", "authorized_meals_index"],
        "Servicio de Alimentación": ["delivery_index", "delivery_show", "authorized_meals_index"],
    }

    for role_name, nombres in permisos_por_rol.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            print(f"No se encontró el rol {role_name}.")
            continue
        for p_name in nombres:
            perm = Permission.query.filter_by(name=p_name).first()
            if not perm:
                perm = Permission(name=p_name)
                db.session.add(perm)
            if perm not in role.permissions:
                role.permissions.append(perm)

    db.session.commit()
    print("Permisos de Entregas asignados.")
