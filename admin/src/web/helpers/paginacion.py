"""Helpers web de la paginación: leer el número de página y armar la respuesta de la API."""


PAGINA_INICIAL = 1


def validar_pagina(valor):
    """Convierte el parámetro ``?page=`` en un entero mayor o igual a 1.

    Si no viene (``None`` o vacío) devuelve 1, porque no mandar la página
    es pedir la primera. Devuelve ``None`` si el valor no es un entero
    o es menor que 1 (por ejemplo ``"abc"``, ``"1.5"``, ``"0"`` o ``"-2"``).
    Cada controlador decide qué hacer con ``None``: las pantallas usan la
    página 1 y la API responde 400.
    """
    if valor is None or str(valor).strip() == "":
        return PAGINA_INICIAL

    try:
        pagina = int(str(valor).strip())
    except ValueError:
        return None

    if pagina < PAGINA_INICIAL:
        return None

    return pagina


def respuesta_paginada(pagina, items):
    """Arma el diccionario de una respuesta paginada de la API.

    Recibe el objeto que devuelve ``paginar`` y la lista de items ya
    convertidos a diccionario por el controlador.
    """
    return {
        "items": items,
        "pagina": pagina.page,
        "por_pagina": pagina.per_page,
        "total": pagina.total,
        "paginas": pagina.pages,
    }
