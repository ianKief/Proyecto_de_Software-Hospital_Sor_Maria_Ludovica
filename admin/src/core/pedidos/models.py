from datetime import datetime, timezone

from src.core.db import db


class Pedido(db.Model):
    """Representa un pedido de comidas de un sector para una fecha."""

    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)

    sector_id = db.Column(
        db.Integer,
        db.ForeignKey("sectors.id"),
        nullable=False,
    )

    fecha = db.Column(
        db.Date,
        nullable=False,
    )

    estado = db.Column(
        db.String(20),
        nullable=False,
        default="confirmado",
    )

    creado_por = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
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

    solicitudes = db.relationship(
        "SolicitudPedido",
        back_populates="pedido",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "sector_id",
            "fecha",
            name="uq_pedido_sector_fecha",
        ),
        db.CheckConstraint(
            "estado IN ('confirmado', 'autorizado', 'rechazado')",
            name="ck_pedido_estado",
        ),
    )


class SolicitudPedido(db.Model):
    """Representa una solicitud nominada de una comida dentro de un pedido."""

    __tablename__ = "solicitudes_pedido"

    id = db.Column(db.Integer, primary_key=True)

    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=False,
    )

    # Referencia al personal.
    person_id = db.Column(
        db.Integer,
        nullable=False,
    )

    # Tipo de comida: desayuno, almuerzo, merienda o cena.
    tipo_comida_id = db.Column(
        db.Integer,
        nullable=False,
    )

    # Tipo de menú que tenía la persona al momento del pedido.
    tipo_menu_id = db.Column(
        db.Integer,
        nullable=False,
    )

    condicion = db.Column(
        db.String(20),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    pedido = db.relationship(
        "Pedido",
        back_populates="solicitudes",
    )

    autorizacion = db.relationship(
        "Autorizacion",
        back_populates="solicitud",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "pedido_id",
            "person_id",
            "tipo_comida_id",
            name="uq_solicitud_persona_comida",
        ),
        db.CheckConstraint(
            "condicion IN ('regular', 'excepcion')",
            name="ck_solicitud_condicion",
        ),
    )


class Autorizacion(db.Model):
    """Representa la autorización individual de una solicitud."""

    __tablename__ = "autorizaciones"

    id = db.Column(db.Integer, primary_key=True)

    solicitud_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitudes_pedido.id"),
        nullable=False,
        unique=True,
    )

    autorizada = db.Column(
        db.Boolean,
        nullable=False,
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    solicitud = db.relationship(
        "SolicitudPedido",
        back_populates="autorizacion",
    )