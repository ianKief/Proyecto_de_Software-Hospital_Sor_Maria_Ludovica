"""Paginación común de los listados, según la configuración del sistema."""
from src.core.configuration import obtener_configuracion


def paginar(consulta, pagina):
    """Pagina una consulta con los elementos por página de la configuración.

    Recibe una consulta estilo ``Modelo.query`` con orden fijo, por ejemplo
    ``User.query.order_by(User.id)``, y el número de página (entero >= 1).
    Sin ``order_by`` las páginas podrían repetir o saltear filas.

    Devuelve el objeto Pagination de Flask-SQLAlchemy (``items``, ``page``,
    ``pages``, ``total``, ``per_page``, ``has_prev``, ``prev_num``,
    ``has_next``, ``next_num``). Si la página es mayor que la última,
    ``items`` viene vacío (no da 404).
    """
    configuracion = obtener_configuracion()
    return consulta.paginate(
        page=pagina,
        per_page=configuracion.elementos_por_pagina,
        error_out=False,
    )
