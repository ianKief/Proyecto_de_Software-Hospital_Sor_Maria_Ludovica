from datetime import datetime, timezone

from src.core.db import db
from src.core.menu_types.models import MenuType
from src.core.personnel_types.models import PersonnelType
from src.core.sectors.models import Sector


class Personal(db.Model):
    """Representa a una persona que puede ser incluida en pedidos de comidas."""

    __tablename__ = "personnel"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    dni = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
    )

    nombre = db.Column(
        db.String(255),
        nullable=False,
    )

    apellido = db.Column(
        db.String(255),
        nullable=False,
    )

    personnel_type_id = db.Column(
        db.Integer,
        db.ForeignKey("personnel_types.id"),
        nullable=False,
    )

    sector_id = db.Column(
        db.Integer,
        db.ForeignKey("sectors.id"),
        nullable=True,
    )

    menu_type_id = db.Column(
        db.Integer,
        db.ForeignKey("menu_types.id"),
        nullable=False,
    )

    activo = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    personnel_type = db.relationship("PersonnelType")
    sector = db.relationship("Sector")
    menu_type = db.relationship("MenuType")