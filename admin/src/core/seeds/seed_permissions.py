from src.web import create_app
from src.core.db import db
from src.core.auth.models import Role, Permission

app = create_app()

PERMISOS_POR_ROL = {
    "Administrador": [
        "user_index",
        "user_new",
        "user_show",
        "user_update",
        "user_block",
        "user_unblock",
        "config_show",
        "config_update",
        "sector_index", 
        "sector_create", 
        "sector_update", 
        "sector_destroy"
    ],
    "Jefe de Servicio": [
        "request_index",
        "request_new",
        "request_show",
        "request_update",
        "request_destroy",
        "summary_requests",
    ],
    "Servicio de Alimentación": [
        "authorization_index",
        "authorization_show",
        "authorization_update",
        "delivery_index",
        "delivery_show",
        "authorized_meals_index",
        "summary_deliveries",
        "summary_requests",
        "summary_authorizations",
    ],
    "Sector Comedor": [
        "delivery_index",
        "delivery_show",
        "delivery_new",
        "authorized_meals_index",
    ],
}

with app.app_context():
    print("Verificando permisos...")

    todos_los_permisos = {
        permiso
        for permisos in PERMISOS_POR_ROL.values()
        for permiso in permisos
    }

    for nombre in todos_los_permisos:
        permiso = Permission.query.filter_by(name=nombre).first()

        if permiso is None:
            db.session.add(Permission(name=nombre))

    db.session.commit()

    for nombre_rol, nombres_permisos in PERMISOS_POR_ROL.items():
        rol = Role.query.filter_by(name=nombre_rol).first()

        if rol is None:
            print(f"No se encontró el rol {nombre_rol}.")
            continue

        for nombre_permiso in nombres_permisos:
            permiso = Permission.query.filter_by(
                name=nombre_permiso
            ).first()

            if permiso not in rol.permissions:
                rol.permissions.append(permiso)

        print(f"Permisos asignados al rol {nombre_rol}.")

    db.session.commit()
    print("Permisos verificados correctamente.")