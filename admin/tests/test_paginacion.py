"""Tests de los helpers web de paginación (no necesitan base de datos)."""
from types import SimpleNamespace

from src.web.helpers.paginacion import respuesta_paginada, validar_pagina


# validar_pagina

def test_pagina_valida():
    assert validar_pagina("1") == 1
    assert validar_pagina("3") == 3


def test_pagina_con_espacios():
    assert validar_pagina(" 2 ") == 2


def test_sin_pagina_es_la_primera():
    assert validar_pagina(None) == 1
    assert validar_pagina("") == 1


def test_pagina_invalida():
    for valor in ["abc", "1.5", "0", "-1"]:
        assert validar_pagina(valor) is None


# respuesta_paginada

def test_respuesta_paginada():
    pagina = SimpleNamespace(page=2, per_page=10, total=23, pages=3)
    items = [{"id": 11}, {"id": 12}]

    assert respuesta_paginada(pagina, items) == {
        "items": [{"id": 11}, {"id": 12}],
        "pagina": 2,
        "por_pagina": 10,
        "total": 23,
        "paginas": 3,
    }


def test_respuesta_paginada_vacia():
    pagina = SimpleNamespace(page=1, per_page=25, total=0, pages=0)

    assert respuesta_paginada(pagina, []) == {
        "items": [],
        "pagina": 1,
        "por_pagina": 25,
        "total": 0,
        "paginas": 0,
    }
