from src.core.db import db


class FoodType(db.Model):
    """Representa un tipo de comida."""

    __tablename__ = "food_types"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    nombre = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
    )