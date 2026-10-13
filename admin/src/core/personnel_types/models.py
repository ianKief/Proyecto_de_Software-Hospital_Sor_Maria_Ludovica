from src.core.db import db


class PersonnelType(db.Model):
    """Representa un tipo de personal."""

    __tablename__ = "personnel_types"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    nombre = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
    )

    requiere_sector = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )