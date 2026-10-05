from datetime import datetime, timezone
from src.core.db import db
from sqlalchemy import CheckConstraint, UniqueConstraint


class Quota(db.Model):
    __tablename__ = 'quotas'

    id = db.Column(db.Integer, primary_key=True)
    sector_id = db.Column(db.Integer, db.ForeignKey('sectors.id'), nullable=False)
    tipo_comida = db.Column(db.String(20), nullable=False)  # Desayuno, Almuerzo, Merienda, Cena
    cantidad = db.Column(db.Integer, nullable=False)

    sector = db.relationship('Sector', backref='quotas')

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('sector_id', 'tipo_comida', name='uq_sector_tipo_comida'),
        CheckConstraint('cantidad > 0', name='chk_quota_cantidad_positiva'),
    )

    def __repr__(self):
        return f'<Quota Sector:{self.sector_id} Comida:{self.tipo_comida} Cantidad:{self.cantidad}>'