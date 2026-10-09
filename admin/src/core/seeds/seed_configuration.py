"""Seed de la configuración general del sistema."""
from src.web import create_app
from src.core.db import db
from src.core.configuration import obtener_configuracion
from src.core.configuration.models import Configuration, ID_CONFIGURACION


def seed_configuration():
    """Crea la fila de configuración con los valores iniciales, si todavía no existe.

    Necesita un contexto de aplicación activo. Si la fila ya existe no la modifica,
    así no se pisan los cambios que haya hecho un Administrador.
    """
    print("Verificando configuración inicial...")
    if db.session.get(Configuration, ID_CONFIGURACION):
        print("La configuración ya existía.")
        return

    # obtener_configuracion() crea la fila con los valores iniciales si no existe.
    obtener_configuracion()
    print("Configuración inicial cargada con éxito.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_configuration()
