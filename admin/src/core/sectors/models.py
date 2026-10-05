from datetime import datetime, timezone

from src.core.db import db


class Sector(db.Model):
    """Representa un sector o servicio del hospital."""

    __tablename__ = "sectors"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    nombre = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
    )

    descripcion = db.Column(
        db.String(500),
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