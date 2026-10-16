"""Modelos del módulo de Entregas."""
from datetime import datetime, timezone

from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.pedidos.models import Autorizacion
from src.core.personnel.models import Personal
from src.core.users.models import User


class Entrega(db.Model):
    """Una entrega de comida del Sector Comedor: un tipo de comida, una o varias personas y quién retira."""

    __tablename__ = "deliveries"

    id = db.Column(db.Integer, primary_key=True)

    # Usuario del Comedor que registra la entrega.
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
    )

    # Persona de Personal que retira (no hace falta que esté en la entrega).
    responsable_id = db.Column(
        db.Integer,
        db.ForeignKey("personnel.id"),
        nullable=False,
    )

    tipo_comida_id = db.Column(
        db.Integer,
        db.ForeignKey("food_types.id"),
        nullable=False,
    )

    # Fecha y hora de la entrega: la pone el servidor al crearla (nunca viene del cliente).
    # Se guarda en UTC y sin zona: si se manda con zona, psycopg2 la envía como timestamptz
    # y Postgres la pasa a la zona de la sesión (issue #18). Para mostrarla: a_hora_argentina().
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    usuario = db.relationship("User")
    responsable = db.relationship("Personal")
    tipo_comida = db.relationship("FoodType")

    detalles = db.relationship(
        "EntregaDetalle",
        back_populates="entrega",
    )


class EntregaDetalle(db.Model):
    """Una autorización entregada dentro de una entrega (una persona y una comida)."""

    __tablename__ = "delivery_items"

    id = db.Column(db.Integer, primary_key=True)

    entrega_id = db.Column(
        db.Integer,
        db.ForeignKey("deliveries.id"),
        nullable=False,
    )

    # UNIQUE: la base impide entregar dos veces la misma autorización.
    autorizacion_id = db.Column(
        db.Integer,
        db.ForeignKey("autorizaciones.id"),
        nullable=False,
        unique=True,
    )

    entrega = db.relationship(
        "Entrega",
        back_populates="detalles",
    )

    autorizacion = db.relationship("Autorizacion")
