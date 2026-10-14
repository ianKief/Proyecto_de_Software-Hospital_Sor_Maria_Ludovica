from datetime import datetime, timezone

from src.core.auth.models import Role
from src.core.db import db
from src.core.sectors.models import Sector


class User(db.Model):
    """Representa un usuario que puede acceder al sistema."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    apellido = db.Column(db.String(255), nullable=False)
    dni = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    
    role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id"),
        nullable=False,
    )
    role = db.relationship("Role")

    sector_id = db.Column(
        db.Integer,
        db.ForeignKey("sectors.id"),
        nullable=True,
    )
    sector = db.relationship('Sector', back_populates='jefes_servicio')

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
