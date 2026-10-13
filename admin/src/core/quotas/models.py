from datetime import datetime, timezone

from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.sectors.models import Sector


class Cupo(db.Model):
    """Representa el cupo de comensales para un sector y tipo de comida."""

    __tablename__ = "quotas"

    id = db.Column(db.Integer, primary_key=True)

    sector_id = db.Column(
        db.Integer,
        db.ForeignKey("sectors.id"),
        nullable=False,
    )

    tipo_comida_id = db.Column(
        db.Integer,
        db.ForeignKey("food_types.id"),
        nullable=False,
    )

    cantidad = db.Column(db.Integer, nullable=False)

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

    sector = db.relationship("Sector")
    tipo_comida = db.relationship("FoodType")

    __table_args__ = (
        db.UniqueConstraint(
            "sector_id",
            "tipo_comida_id",
            name="uq_cupo_sector_tipo_comida",
        ),
        db.CheckConstraint(
            "cantidad > 0",
            name="ck_cupo_cantidad_positiva",
        ),
    )