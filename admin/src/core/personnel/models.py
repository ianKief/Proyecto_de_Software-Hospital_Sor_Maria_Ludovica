from datetime import datetime, timezone
from src.core.db import db


class PersonnelType(db.Model):
    __tablename__ = 'personnel_types'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    requiere_sector = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<PersonnelType {self.nombre}>'


class MenuType(db.Model):
    __tablename__ = 'menu_types'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<MenuType {self.nombre}>'


class Personnel(db.Model):
    __tablename__ = 'personnel'

    id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Claves foráneas obligatorias
    personnel_type_id = db.Column(db.Integer, db.ForeignKey('personnel_types.id'), nullable=False)
    menu_type_id = db.Column(db.Integer, db.ForeignKey('menu_types.id'), nullable=False)

    # Sector es opcional (nullable=True) porque Residentes y Eventuales no tienen sector fijo
    sector_id = db.Column(db.Integer, db.ForeignKey('sectors.id'), nullable=True)

    # Relaciones de conveniencia
    personnel_type = db.relationship('PersonnelType', backref='personnel')
    menu_type = db.relationship('MenuType', backref='personnel')
    sector = db.relationship('Sector', backref='personnel')

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Personnel {self.apellido}, {self.nombre} (DNI: {self.dni})>'