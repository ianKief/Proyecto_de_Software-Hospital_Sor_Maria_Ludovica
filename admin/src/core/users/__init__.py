import secrets
import bcrypt
from sqlalchemy import or_
from src.core.db import db
from src.core.users.models import User
from src.core.auth.models import Role
from src.core.users.exceptions import UserNotFoundError, RoleNotFoundError

def get_user_by_id(user_id):
    """Obtiene un usuario por su ID."""
    return User.query.get(user_id)

def get_all_roles():
    """Obtiene todos los roles disponibles en el sistema (útil para el formulario web)."""
    return Role.query.order_by(Role.name).all()

def assign_role(user_id, role_id):
    """
    Asigna un nuevo rol a un usuario existente.
    Si el usuario deja de ser Jefe de Servicio, se lo desvincula de sus sectores.
    """
    user = get_user_by_id(user_id)
    if not user:
        raise UserNotFoundError("El usuario especificado no existe.")

    new_role = Role.query.get(role_id)
    if not new_role:
        raise RoleNotFoundError("El rol especificado no es válido.")

    if user.role_id == new_role.id:
        return user

    old_role = Role.query.get(user.role_id)
    if old_role and old_role.name == "Jefe de Servicio":
       user.sector_id = None

    user.role_id = new_role.id
    
    db.session.commit()
    
    return user


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




def obtener_usuario(id=None, email=None, dni=None):
    """Busca y retorna un único usuario según el criterio especificado.
    
    Permite filtrar por 'id', 'email' o 'dni'. Devuelve el objeto User si existe, o None.
    """
    if id is None and email is None and dni is None:
        return None

    query = User.query

    if id is not None:
        query = query.filter(User.id == id)
    if email is not None:
        query = query.filter(User.email == email.strip())
    if dni is not None:
        query = query.filter(User.dni == str(dni).strip())

    return query.first()


def actualizar_contrasena(user, nueva_contrasena):
    """Actualiza la contraseña del usuario con hash seguro bcrypt, activa su cuenta y guarda los cambios."""
    if not nueva_contrasena or len(nueva_contrasena.strip()) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")

    hashed_password = bcrypt.hashpw(nueva_contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.password = hashed_password
    user.activo = True
    db.session.commit()
    return user


def crear_usuario(email, nombre, apellido, dni, role_id=None, password=None, sector_id=None, activo=True):
    """Crea y persiste un nuevo usuario en la base de datos.
    
    Si no se especifica una contraseña, genera una contraseña temporal aleatoria segura.
    Soporta llamada con role_id o con password en 5ta posición por compatibilidad.
    """
    # Compatibilidad posicional si se pasó password como 5to argumento
    if isinstance(role_id, str) and not role_id.isdigit() and (password is None or isinstance(password, int)):
        role_id, password = password, role_id

    role = Role.query.get(role_id) if role_id else None
    # Regla de negocio: solo Jefe de Servicio tiene sector asignado
    if not role or role.name != "Jefe de Servicio":
        sector_id = None

    if not password or not str(password).strip():
        password = secrets.token_urlsafe(16)

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


def eliminar_usuario_fisicamente(user):
    """Elimina permanentemente a un usuario de la base de datos (Baja Física)."""
    if user.role and user.role.name == "Administrador":
        raise ValueError("Los usuarios con rol Administrador no pueden ser eliminados.")

    try:
        db.session.delete(user)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        raise


