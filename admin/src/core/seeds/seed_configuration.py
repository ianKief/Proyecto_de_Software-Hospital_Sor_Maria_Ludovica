"""Seed de la configuración general del sistema."""
from src.web import create_app
from src.core.db import db
from src.core.configuration.models import Configuration


def seed_configuration():
    """Crea la fila de configuración con los valores iniciales, si todavía no existe.

    Necesita un contexto de aplicación activo. Si la fila ya existe no la modifica,
    así no se pisan los cambios que haya hecho un Administrador.
    """
    print("Verificando configuración inicial...")
    if Configuration.query.first():
        print("La configuración ya existía.")
        return

    try:
        db.session.add(Configuration(elementos_por_pagina=25, mantenimiento_activo=False))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    print("Configuración inicial cargada con éxito.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_configuration()
