ROL_ADMINISTRADOR = "Administrador"
ROL_JEFE_SERVICIO = "Jefe de Servicio"
ROL_SERVICIO_ALIMENTACION = "Servicio de Alimentación"
ROL_SECTOR_COMEDOR = "Sector Comedor"

def list_users(): # mock up de usuarios
    return  [ {
        "email": "martin.gomez@example.com",
        "nombre": "Martín",
        "apellido": "Gómez",
        "dni": "30123456",
        "password": "Admin#2024",
        "activo": True,
        "rol": ROL_ADMINISTRADOR,
    },
    {
        "email": "laura.fernandez@example.com",
        "nombre": "Laura",
        "apellido": "Fernández",
        "dni": "28987654",
        "password": "Jefe#2024",
        "activo": True,
        "rol": ROL_JEFE_SERVICIO,
    },
    {
        "email": "carlos.rodriguez@example.com",
        "nombre": "Carlos",
        "apellido": "Rodríguez",
        "dni": "33456789",
        "password": "Alimentacion#2024",
        "activo": False,
        "rol": ROL_SERVICIO_ALIMENTACION,
    },
    {
        "email": "sofia.lopez@example.com",
        "nombre": "Sofía",
        "apellido": "López",
        "dni": "35678901",
        "password": "Comedor#2024",
        "activo": True,
        "rol": ROL_SECTOR_COMEDOR,
    }]