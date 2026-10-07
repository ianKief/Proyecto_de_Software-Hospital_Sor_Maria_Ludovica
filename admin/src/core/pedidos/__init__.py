from calendar import monthrange
from datetime import date, timedelta

from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.personnel.models import Personal
from src.core.quotas.models import Cupo
from src.core.pedidos.models import Pedido, SolicitudPedido


def _generar_fechas_pedido(periodicidad, fecha_desde, fecha_hasta):
    """Genera las fechas según la periodicidad indicada."""
    fechas = []

    if periodicidad == "diaria":
        fecha = fecha_desde

        while fecha <= fecha_hasta:
            fechas.append(fecha)
            fecha += timedelta(days=1)

    elif periodicidad == "semanal":
        fecha = fecha_desde

        while fecha <= fecha_hasta:
            fechas.append(fecha)
            fecha += timedelta(days=7)

    elif periodicidad == "mensual":
        fecha = fecha_desde
        dia_original = fecha_desde.day

        while fecha <= fecha_hasta:
            fechas.append(fecha)

            if fecha.month == 12:
                siguiente_anio = fecha.year + 1
                siguiente_mes = 1
            else:
                siguiente_anio = fecha.year
                siguiente_mes = fecha.month + 1

            ultimo_dia = monthrange(
                siguiente_anio,
                siguiente_mes,
            )[1]

            siguiente_dia = min(dia_original, ultimo_dia)

            fecha = date(
                siguiente_anio,
                siguiente_mes,
                siguiente_dia,
            )

    return fechas


def _obtener_tipos_comida():
    """Devuelve los tipos de comida indexados por nombre."""
    tipos = FoodType.query.all()

    return {
        tipo.nombre.lower(): tipo
        for tipo in tipos
    }


def _crear_solicitudes(pedido, detalle, sector_id):
    """Crea las solicitudes nominadas de un pedido."""
    tipos_comida = _obtener_tipos_comida()
    regular_actual = {}

    for nombre_comida, personas_ids in detalle.items():
        if not personas_ids:
            continue

        food_type = tipos_comida.get(nombre_comida)

        if not food_type:
            raise ValueError(
                f"No existe el tipo de comida '{nombre_comida}'"
            )

        cupo = Cupo.query.filter_by(
            sector_id=sector_id,
            tipo_comida_id=food_type.id,
        ).first()

        if not cupo:
            raise ValueError(
                f"No existe un cupo configurado para {nombre_comida}"
            )

        regular_actual[nombre_comida] = (
            SolicitudPedido.query
            .join(Pedido)
            .filter(
                Pedido.sector_id == sector_id,
                Pedido.fecha == pedido.fecha,
                SolicitudPedido.tipo_comida_id == food_type.id,
                SolicitudPedido.condicion == "regular",
            )
            .count()
        )

        for person_id in personas_ids:
            persona = Personal.query.get(person_id)

            if not persona:
                raise ValueError(
                    f"La persona {person_id} no existe"
                )

            if not persona.activo:
                raise ValueError(
                    f"La persona {person_id} se encuentra inactiva"
                )

            tipo_personal = persona.personnel_type

            if not tipo_personal:
                raise ValueError(
                    f"La persona {person_id} no tiene tipo de personal"
                )

            if tipo_personal.nombre == "Personal Fijo":
                if persona.sector_id != sector_id:
                    raise ValueError(
                        f"La persona {person_id} no pertenece "
                        "al sector del Jefe de Servicio"
                    )

            elif tipo_personal.nombre != "Residente":
                raise ValueError(
                    f"La persona {person_id} tiene un tipo de personal "
                    f"no contemplado: {tipo_personal.nombre}"
                )

            if regular_actual[nombre_comida] < cupo.cantidad:
                condicion = "regular"
                regular_actual[nombre_comida] += 1
            else:
                condicion = "excepcion"

            solicitud = SolicitudPedido(
                pedido=pedido,
                person_id=persona.id,
                tipo_comida_id=food_type.id,
                tipo_menu_id=persona.menu_type_id,
                condicion=condicion,
            )

            db.session.add(solicitud)


def crear_pedidos(usuario, resultado):
    """Crea los pedidos y sus solicitudes nominadas."""
    if not usuario.activo:
        raise ValueError(
            "El usuario se encuentra desactivado"
        )

    if not usuario.sector_id:
        raise ValueError(
            "El Jefe de Servicio no tiene un sector asociado"
        )

    sector = usuario.sector

    if not sector:
        raise ValueError(
            "El sector del usuario no existe"
        )

    if not sector.activo:
        raise ValueError(
            "El sector del usuario se encuentra inactivo"
        )

    fechas = _generar_fechas_pedido(
        resultado["periodicidad"],
        resultado["fecha_desde"],
        resultado["fecha_hasta"],
    )

    pedidos_existentes = (
        Pedido.query
        .filter(
            Pedido.sector_id == sector.id,
            Pedido.fecha.in_(fechas),
        )
        .all()
    )

    if pedidos_existentes:
        raise ValueError(
            "Ya existe un pedido para una o más fechas del período"
        )

    pedidos_creados = []

    try:
        for fecha in fechas:
            pedido = Pedido(
                sector_id=sector.id,
                fecha=fecha,
                estado="confirmado",
                creado_por=usuario.id,
            )

            db.session.add(pedido)
            db.session.flush()

            _crear_solicitudes(
                pedido=pedido,
                detalle=resultado["detalle"],
                sector_id=sector.id,
            )

            pedidos_creados.append(pedido)

        db.session.commit()

        return pedidos_creados

    except Exception:
        db.session.rollback()
        raise