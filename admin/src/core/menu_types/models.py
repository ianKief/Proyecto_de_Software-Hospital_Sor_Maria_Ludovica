from src.core.db import db


class MenuType(db.Model):
    """Representa un tipo de menú."""

    __tablename__ = "menu_types"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    nombre = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
    )