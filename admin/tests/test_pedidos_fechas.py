from datetime import date, timedelta

from src.core.pedidos import _generar_fechas_pedido


def test_carga_diaria_genera_un_pedido_por_dia():
    fechas = _generar_fechas_pedido(
        "diaria",
        date(2026, 10, 12),
        date(2026, 10, 14),
    )

    assert fechas == [
        date(2026, 10, 12),
        date(2026, 10, 13),
        date(2026, 10, 14),
    ]


def test_carga_semanal_genera_un_pedido_por_cada_dia():
    fechas = _generar_fechas_pedido(
        "semanal",
        date(2026, 10, 12),
        date(2026, 10, 18),
    )

    assert fechas == [
        date(2026, 10, 12) + timedelta(days=i)
        for i in range(7)
    ]


def test_carga_mensual_genera_un_pedido_por_cada_dia():
    fechas = _generar_fechas_pedido(
        "mensual",
        date(2026, 10, 1),
        date(2026, 10, 31),
    )

    assert len(fechas) == 31
    assert fechas[0] == date(2026, 10, 1)
    assert fechas[-1] == date(2026, 10, 31)