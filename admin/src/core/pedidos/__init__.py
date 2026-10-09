from calendar import monthrange
from datetime import date, timedelta

from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.personnel.models import Personal
from src.core.quotas.models import Cupo
from src.core.pedidos.models import Pedido, SolicitudPedido
from src.core.menu_types.models import MenuType


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
    regular_actual = 0

    food_type = pedido.tipo_comida
    nombre_comida = food_type.nombre.lower()
    personas_ids = detalle.get(nombre_comida, [])

    cupo = Cupo.query.filter_by(
        sector_id=sector_id,
        tipo_comida_id=food_type.id,
    ).first()

    if cupo:
        regular_actual = (
            SolicitudPedido.query
            .join(Pedido)
            .filter(
                Pedido.sector_id == sector_id,
                Pedido.fecha == pedido.fecha,
                Pedido.tipo_comida_id == food_type.id,
                Pedido.id != pedido.id,
                SolicitudPedido.condicion == "regular",
            )
            .count()
        )

    for person_id in personas_ids:
        persona = Personal.query.get(person_id)

        if not persona:
            raise ValueError(f"La persona {person_id} no existe")

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

        if cupo and regular_actual < cupo.cantidad:
            condicion = "regular"
            regular_actual += 1
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
    """Crea un pedido por fecha y tipo de comida."""
    if not usuario.activo:
        raise ValueError("El usuario se encuentra desactivado")

    if not usuario.sector_id:
        raise ValueError(
            "El Jefe de Servicio no tiene un sector asociado"
        )

    sector = usuario.sector

    if not sector:
        raise ValueError("El sector del usuario no existe")

    if not sector.activo:
        raise ValueError("El sector del usuario se encuentra inactivo")

    fechas = _generar_fechas_pedido(
        resultado["periodicidad"],
        resultado["fecha_desde"],
        resultado["fecha_hasta"],
    )

    tipos_comida = _obtener_tipos_comida()
    detalle = resultado["detalle"]

    comidas_con_personas = []

    for nombre, personas in detalle.items():
        if not personas:
            continue

        food_type = tipos_comida.get(nombre)

        if not food_type:
            raise ValueError(
                f"No existe el tipo de comida '{nombre}'"
            )

        comidas_con_personas.append((food_type, personas))

    if not comidas_con_personas:
        raise ValueError(
            "Debe existir al menos una persona en alguna comida"
        )

    pedidos_creados = []

    try:
        for fecha in fechas:
            for food_type, personas in comidas_con_personas:
                existente = Pedido.query.filter_by(
                    sector_id=sector.id,
                    fecha=fecha,
                    tipo_comida_id=food_type.id,
                ).first()

                if existente:
                    raise ValueError(
                        f"Ya existe un pedido de {food_type.nombre} "
                        f"para la fecha {fecha}"
                    )

                pedido = Pedido(
                    sector_id=sector.id,
                    fecha=fecha,
                    tipo_comida_id=food_type.id,
                    estado="confirmado",
                    creado_por=usuario.id,
                )

                db.session.add(pedido)
                db.session.flush()

                _crear_solicitudes(
                    pedido=pedido,
                    detalle={
                        food_type.nombre.lower(): personas,
                    },
                    sector_id=sector.id,
                )

                pedidos_creados.append(pedido)

        db.session.commit()
        return pedidos_creados

    except Exception:
        db.session.rollback()
        raise

def listar_pedidos(
    usuario,
    fecha_desde=None,
    fecha_hasta=None,
    estado=None,
    tipo_comida=None,
    tipo_menu=None,
    pagina=1,
    por_pagina=25,
):
    """Lista los pedidos del sector del Jefe de Servicio."""
    if not usuario.activo:
        raise ValueError("El usuario se encuentra desactivado")

    if not usuario.sector_id:
        raise ValueError(
            "El Jefe de Servicio no tiene un sector asociado"
        )

    query = Pedido.query.filter_by(
        sector_id=usuario.sector_id
    )

    if fecha_desde:
        query = query.filter(Pedido.fecha >= fecha_desde)

    if fecha_hasta:
        query = query.filter(Pedido.fecha <= fecha_hasta)

    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ValueError(
            "fecha_hasta no puede ser anterior a fecha_desde"
        )

    estados_validos = {
        "confirmado",
        "autorizado",
        "rechazado",
    }

    if estado:
        if estado not in estados_validos:
            raise ValueError("Estado inválido")

        query = query.filter(Pedido.estado == estado)

    if tipo_comida:
        food_type = FoodType.query.filter(
            db.func.lower(FoodType.nombre) == tipo_comida.lower()
        ).first()

        if not food_type:
            raise ValueError("Tipo de comida inexistente")

        query = query.filter(
            Pedido.solicitudes.any(
                SolicitudPedido.tipo_comida_id == food_type.id
            )
        )

    if tipo_menu:
        menu_type = MenuType.query.filter(
            db.func.lower(MenuType.nombre) == tipo_menu.lower()
        ).first()

        if not menu_type:
            raise ValueError("Tipo de menú inexistente")

        query = query.filter(
            Pedido.solicitudes.any(
                SolicitudPedido.tipo_menu_id == menu_type.id
            )
        )

    por_pagina = min(por_pagina, 25)

    total = query.count()

    pedidos = (
        query
        .order_by(Pedido.fecha.desc(), Pedido.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    return pedidos, total

def consultar_pedido(usuario, pedido_id):
    """Obtiene el detalle de un pedido del sector del usuario."""
    if not usuario.activo:
        raise ValueError("Usuario no válido")

    if usuario.sector_id is None:
        raise PermissionError("El usuario no tiene un sector asignado")

    pedido = Pedido.query.get(pedido_id)

    if pedido is None:
        raise LookupError("Pedido no encontrado")

    if pedido.sector_id != usuario.sector_id:
        raise PermissionError(
            "No autorizado para consultar este pedido"
        )

    solicitudes = (
        SolicitudPedido.query
        .filter_by(pedido_id=pedido.id)
        .all()
    )

    totales_comida = {
        "desayuno": {"solicitadas": 0, "autorizadas": 0},
        "almuerzo": {"solicitadas": 0, "autorizadas": 0},
        "merienda": {"solicitadas": 0, "autorizadas": 0},
        "cena": {"solicitadas": 0, "autorizadas": 0},
    }

    totales_menu = {}

    detalle = []

    for solicitud in solicitudes:
        nombre_comida = solicitud.food_type.nombre.lower()
        nombre_menu = solicitud.menu_type.nombre

        autorizada = (
            solicitud.autorizacion is not None
            and solicitud.autorizacion.autorizada
        )

        if nombre_comida not in totales_comida:
            totales_comida[nombre_comida] = {
                "solicitadas": 0,
                "autorizadas": 0,
            }

        totales_comida[nombre_comida]["solicitadas"] += 1

        if autorizada:
            totales_comida[nombre_comida]["autorizadas"] += 1

        if nombre_menu not in totales_menu:
            totales_menu[nombre_menu] = {
                "solicitadas": 0,
                "autorizadas": 0,
            }

        totales_menu[nombre_menu]["solicitadas"] += 1

        if autorizada:
            totales_menu[nombre_menu]["autorizadas"] += 1

        detalle.append({
            "solicitud_id": solicitud.id,
            "persona": {
                "id": solicitud.persona.id,
                "dni": solicitud.persona.dni,
                "nombre": solicitud.persona.nombre,
                "apellido": solicitud.persona.apellido,
            },
            "tipo_comida": {
                "id": solicitud.tipo_comida_id,
                "nombre": solicitud.food_type.nombre,
            },
            "tipo_menu": {
                "id": solicitud.tipo_menu_id,
                "nombre": solicitud.menu_type.nombre,
            },
            "condicion": solicitud.condicion,
            "autorizacion": {
                "autorizada": (
                    solicitud.autorizacion.autorizada
                    if solicitud.autorizacion is not None
                    else None
                ),
                "usuario_id": (
                    solicitud.autorizacion.usuario_id
                    if solicitud.autorizacion is not None
                    else None
                ),
            },
        })

    return pedido, solicitudes, totales_comida, totales_menu, detalle

def modificar_pedido(usuario, pedido_id, resultado):
    """Modifica un pedido confirmado del sector del usuario."""
    if usuario.sector_id is None:
        raise PermissionError(
            "El Jefe de Servicio no tiene un sector asignado"
        )

    pedido = Pedido.query.get(pedido_id)

    if pedido is None:
        raise LookupError("Pedido no encontrado")

    if pedido.sector_id != usuario.sector_id:
        raise PermissionError(
            "No autorizado para modificar este pedido"
        )

    if pedido.estado != "confirmado":
        raise RuntimeError(
            "Solo se pueden modificar pedidos confirmados"
        )

    if resultado["fecha_desde"] != resultado["fecha_hasta"]:
        raise ValueError(
            "La modificación de pedidos con rango de fechas "
            "todavía no está implementada"
        )

    nueva_fecha = resultado["fecha_desde"]

    pedido_existente = Pedido.query.filter(
        Pedido.sector_id == pedido.sector_id,
        Pedido.fecha == nueva_fecha,
        Pedido.tipo_comida_id == pedido.tipo_comida_id,
        Pedido.id != pedido.id,
    ).first()

    if pedido_existente:
        raise RuntimeError(
            "Ya existe un pedido para ese sector, fecha y tipo de comida"
        )

    nombre_comida = pedido.tipo_comida.nombre.lower()
    personas = resultado["detalle"].get(nombre_comida, [])

    if not personas:
        raise ValueError(
            "La modificación debe incluir personas para "
            f"{pedido.tipo_comida.nombre}"
        )

    otras_comidas = {
        nombre: ids
        for nombre, ids in resultado["detalle"].items()
        if nombre != nombre_comida and ids
    }

    if otras_comidas:
        raise ValueError(
            "Un pedido solo puede contener un tipo de comida"
        )

    try:
        solicitudes_actuales = (
            SolicitudPedido.query
            .filter_by(pedido_id=pedido.id)
            .all()
        )

        for solicitud in solicitudes_actuales:
            if solicitud.autorizacion is not None:
                db.session.delete(solicitud.autorizacion)

            db.session.delete(solicitud)

        pedido.fecha = nueva_fecha

        db.session.flush()

        _crear_solicitudes(
            pedido=pedido,
            detalle=resultado["detalle"],
            sector_id=usuario.sector_id,
        )

        db.session.commit()

        return pedido

    except Exception:
        db.session.rollback()
        raise

def eliminar_pedido(usuario, pedido_id):
    """Elimina un pedido confirmado del sector del usuario."""
    if usuario is None or not usuario.activo:
        raise ValueError("Usuario no válido")

    if usuario.sector_id is None:
        raise PermissionError(
            "El Jefe de Servicio no tiene un sector asignado"
        )

    pedido = Pedido.query.get(pedido_id)

    if pedido is None:
        raise LookupError("Pedido no encontrado")

    if pedido.sector_id != usuario.sector_id:
        raise PermissionError(
            "No autorizado para eliminar este pedido"
        )

    if pedido.estado != "confirmado":
        raise RuntimeError(
            "Solo se pueden eliminar pedidos confirmados"
        )

    try:
        solicitudes = (
            SolicitudPedido.query
            .filter_by(pedido_id=pedido.id)
            .all()
        )

        for solicitud in solicitudes:
            if solicitud.autorizacion is not None:
                db.session.delete(solicitud.autorizacion)

            db.session.delete(solicitud)

        db.session.delete(pedido)
        db.session.commit()

    except Exception:
        db.session.rollback()
        raise