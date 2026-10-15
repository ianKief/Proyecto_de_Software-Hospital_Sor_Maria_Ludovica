import bcrypt
from sqlalchemy import or_
from src.core.db import db
from src.core.users.models import User
from src.core.auth.models import Role

def get_jefes_disponibles() -> list[User]:
    """
    Retorna la lista de usuarios activos que tienen el rol 'Jefe de Servicio' 
    y que actualmente no están asignados a ningún sector.
    """
    return User.query.join(Role).filter(
        User.sector_id == None, 
        User.activo == True,
        Role.name == 'Jefe de Servicio'
    ).all()

def buscar_usuarios(email=None, nombre_apellido=None, dni=None, activo=None, role_id=None, sector_id=None, order_by='created_at', order_dir='desc'):
    """Construye y devuelve la consulta SQLAlchemy con los filtros y ordenamiento especificados."""
    query = User.query

    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
    if nombre_apellido:
        query = query.filter(or_(User.nombre.ilike(f"%{nombre_apellido}%"), User.apellido.ilike(f"%{nombre_apellido}%")))
    if dni:
        query = query.filter(User.dni.ilike(f"%{dni}%"))
    if activo in ['true', '1']:
        query = query.filter(User.activo.is_(True))
    elif activo in ['false', '0']:
        query = query.filter(User.activo.is_(False))
    if role_id and str(role_id).isdigit():
        query = query.filter(User.role_id == int(role_id))
    if sector_id and str(sector_id).isdigit():
        query = query.filter(User.sector_id == int(sector_id))

    if order_by == 'email':
        order_clause = [User.email.desc() if order_dir == 'desc' else User.email.asc()]
    elif order_by == 'apellido_nombre':
        order_clause = [
            User.apellido.desc() if order_dir == 'desc' else User.apellido.asc(),
            User.nombre.desc() if order_dir == 'desc' else User.nombre.asc()
        ]
    else:
        order_clause = [User.created_at.desc() if order_dir == 'desc' else User.created_at.asc()]

    return query.order_by(*order_clause)


def existe_usuario_con_email(email, excluir_id=None):
    """Verifica si ya existe un usuario registrado con el correo electrónico especificado."""
    query = User.query.filter(User.email == email)
    if excluir_id is not None:
        query = query.filter(User.id != excluir_id)
    return query.first() is not None


def existe_usuario_con_dni(dni, excluir_id=None):
    """Verifica si ya existe un usuario registrado con el DNI especificado."""
    query = User.query.filter(User.dni == dni)
    if excluir_id is not None:
        query = query.filter(User.id != excluir_id)
    return query.first() is not None


def crear_usuario(email, nombre, apellido, dni, password, role_id, sector_id=None, activo=True):
    """Crea y persiste un nuevo usuario en la base de datos."""
    role = Role.query.get(role_id)
    # Regla de negocio: solo Jefe de Servicio tiene sector asignado
    if not role or role.name != "Jefe de Servicio":
        sector_id = None

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    new_user = User(
        email=email,
        nombre=nombre,
        apellido=apellido,
        dni=dni,
        password=hashed_password,
        activo=activo,
        role_id=role_id,
        sector_id=sector_id
    )

    db.session.add(new_user)
    db.session.commit()
    return new_user


def actualizar_usuario(user, email, nombre, apellido, dni, role_id, sector_id=None, activo=True, password=None):
    """Actualiza los datos de un usuario existente y persiste los cambios."""
    role = Role.query.get(role_id)
    if not role or role.name != "Jefe de Servicio":
        sector_id = None

    # Regla de negocio: los administradores no pueden ser bloqueados
    if role and role.name == "Administrador" and not activo:
        raise ValueError("Los usuarios con rol Administrador no pueden ser bloqueados.")

    user.email = email
    user.nombre = nombre
    user.apellido = apellido
    user.dni = dni
    user.role_id = role_id
    user.sector_id = sector_id
    user.activo = activo

    if password and password.strip():
        user.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    db.session.commit()
    return user


def bloquear_usuario(user):
    """Bloquea a un usuario en el sistema."""
    if user.role.name == "Administrador":
        raise ValueError("Los usuarios con rol Administrador no pueden ser bloqueados.")

    user.activo = False
    db.session.commit()
    return user


def desbloquear_usuario(user):
    """Desbloquea a un usuario en el sistema."""
    user.activo = True
    db.session.commit()
    return user

