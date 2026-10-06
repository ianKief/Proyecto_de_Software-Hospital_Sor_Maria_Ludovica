from datetime import date

from flask import Blueprint, jsonify, request, session

from src.core.db import db
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.personnel.models import Personal
from src.core.pedidos.models import Pedido, SolicitudPedido
from src.core.quotas.models import Cupo
from src.core.sectors.models import Sector
from src.core.users.models import User
from src.web.helpers.pedidos_validaciones import validar_pedido


pedidos_bp = Blueprint(
    "pedidos",
    __name__,
    url_prefix="/api/requests",
)


def _obtener_usuario_autenticado():
    """Obtiene el usuario autenticado a partir de la sesión."""

    user_id = session.get("user_id")

    if not user_id:
        return None

    return User.query.get(user_id)


def _obtener_tipos_comida():
    """Devuelve los tipos de comida indexados por nombre normalizado."""

    tipos = FoodType.query.all()

    return {
        tipo.nombre.lower(): tipo
        for tipo in tipos
    }


def _crear_solicitudes(
    pedido,
    detalle,
    sector_id,
):
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


@pedidos_bp.route("", methods=["POST"])
def crear_pedido():
    """Crea un pedido y sus solicitudes nominadas."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "El cuerpo de la solicitud es obligatorio",
        }), 400

    es_valido, resultado = validar_pedido(data)

    if not es_valido:
        return jsonify(resultado), 400

    # La semántica de cargas semanales/mensuales todavía no está
    # definida explícitamente en el TP. Por ahora persistimos pedidos
    # de una fecha puntual.
    if resultado["fecha_desde"] != resultado["fecha_hasta"]:
        return jsonify({
            "error": (
                "La creación de pedidos con rango de fechas "
                "todavía no está implementada"
            ),
        }), 400

    usuario = _obtener_usuario_autenticado()

    if not usuario:
        return jsonify({
            "error": "Usuario no autenticado",
        }), 401

    if not usuario.activo:
        return jsonify({
            "error": "El usuario se encuentra desactivado",
        }), 403

    if not usuario.sector_id:
        return jsonify({
            "error": "El Jefe de Servicio no tiene un sector asociado",
        }), 400

    sector = usuario.sector

    if not sector:
        return jsonify({
            "error": "El sector del usuario no existe",
        }), 400

    if not sector.activo:
        return jsonify({
            "error": "El sector del usuario se encuentra inactivo",
        }), 400

    fecha = resultado["fecha_desde"]

    pedido_existente = Pedido.query.filter_by(
        sector_id=sector.id,
        fecha=fecha,
    ).first()

    if pedido_existente:
        return jsonify({
            "error": "Ya existe un pedido para ese sector y fecha",
            "request_id": pedido_existente.id,
        }), 409

    pedido = Pedido(
        sector_id=sector.id,
        fecha=fecha,
        estado="confirmado",
        creado_por=usuario.id,
    )

    try:
        db.session.add(pedido)
        db.session.flush()

        _crear_solicitudes(
            pedido=pedido,
            detalle=resultado["detalle"],
            sector_id=sector.id,
        )

        db.session.commit()

    except ValueError as exc:
        db.session.rollback()

        return jsonify({
            "error": str(exc),
        }), 400

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "No se pudo crear el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido creado correctamente",
        "pedido": {
            "id": pedido.id,
            "sector_id": pedido.sector_id,
            "fecha": pedido.fecha.isoformat(),
            "estado": pedido.estado,
            "creado_por": pedido.creado_por,
            "solicitudes": [
                {
                    "id": solicitud.id,
                    "person_id": solicitud.person_id,
                    "tipo_comida_id": solicitud.tipo_comida_id,
                    "tipo_menu_id": solicitud.tipo_menu_id,
                    "condicion": solicitud.condicion,
                }
                for solicitud in pedido.solicitudes
            ],
        },
    }), 201


@pedidos_bp.route("", methods=["GET"])
def listar_pedidos():
    """Lista los pedidos del sector del Jefe de Servicio autenticado."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    usuario = _obtener_usuario_autenticado()

    if not usuario:
        return jsonify({
            "error": "Usuario no autenticado",
        }), 401

    if not usuario.activo:
        return jsonify({
            "error": "El usuario se encuentra desactivado",
        }), 403

    if not usuario.sector_id:
        return jsonify({
            "error": "El Jefe de Servicio no tiene un sector asociado",
        }), 400

    # El sector SIEMPRE sale del usuario autenticado.
    query = Pedido.query.filter_by(
        sector_id=usuario.sector_id,
    )

    # Filtro por rango de fechas.
    fecha_desde_param = request.args.get("fecha_desde")
    fecha_hasta_param = request.args.get("fecha_hasta")

    if fecha_desde_param:
        try:
            fecha_desde = date.fromisoformat(fecha_desde_param)
        except ValueError:
            return jsonify({
                "error": "fecha_desde debe tener formato YYYY-MM-DD",
            }), 400

        query = query.filter(Pedido.fecha >= fecha_desde)

    if fecha_hasta_param:
        try:
            fecha_hasta = date.fromisoformat(fecha_hasta_param)
        except ValueError:
            return jsonify({
                "error": "fecha_hasta debe tener formato YYYY-MM-DD",
            }), 400

        query = query.filter(Pedido.fecha <= fecha_hasta)

    if (
        fecha_desde_param
        and fecha_hasta_param
        and fecha_desde > fecha_hasta
    ):
        return jsonify({
            "error": "fecha_hasta no puede ser anterior a fecha_desde",
        }), 400

    # Filtro por estado.
    estado = request.args.get("estado")

    estados_validos = {
        "confirmado",
        "autorizado",
        "rechazado",
    }

    if estado:
        if estado not in estados_validos:
            return jsonify({
                "error": "Estado inválido",
                "valores_permitidos": sorted(estados_validos),
            }), 400

        query = query.filter(Pedido.estado == estado)

    # Filtro por tipo de comida.
    tipo_comida = request.args.get("tipo_comida")

    if tipo_comida:
        food_type = FoodType.query.filter(
            db.func.lower(FoodType.nombre) == tipo_comida.lower()
        ).first()

        if not food_type:
            return jsonify({
                "error": "Tipo de comida inexistente",
            }), 400

        query = query.filter(
            Pedido.solicitudes.any(
                SolicitudPedido.tipo_comida_id == food_type.id
            )
        )

    # Filtro por tipo de menú.
    tipo_menu = request.args.get("tipo_menu")

    if tipo_menu:
        menu_type = MenuType.query.filter(
            db.func.lower(MenuType.nombre) == tipo_menu.lower()
        ).first()

        if not menu_type:
            return jsonify({
                "error": "Tipo de menú inexistente",
            }), 400

        query = query.filter(
            Pedido.solicitudes.any(
                SolicitudPedido.tipo_menu_id == menu_type.id
            )
        )

    # Paginación.
    try:
        pagina = int(request.args.get("pagina", 1))
        por_pagina = int(request.args.get("por_pagina", 25))
    except ValueError:
        return jsonify({
            "error": "pagina y por_pagina deben ser números enteros",
        }), 400

    if pagina < 1:
        return jsonify({
            "error": "pagina debe ser mayor o igual a 1",
        }), 400

    if por_pagina < 1:
        return jsonify({
            "error": "por_pagina debe ser mayor o igual a 1",
        }), 400

    # El TP fija un máximo de 25.
    por_pagina = min(por_pagina, 25)

    total = query.count()

    pedidos = (
        query
        .order_by(Pedido.fecha.desc(), Pedido.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    resultado = []

    for pedido in pedidos:
        solicitudes = pedido.solicitudes

        totales_comida = {
            "desayuno": 0,
            "almuerzo": 0,
            "merienda": 0,
            "cena": 0,
        }

        totales_menu = {
            "General": 0,
            "Vegetariano": 0,
            "Celiaco": 0,
        }

        for solicitud in solicitudes:
            if solicitud.food_type:
                nombre_comida = solicitud.food_type.nombre.lower()

                if nombre_comida in totales_comida:
                    totales_comida[nombre_comida] += 1

            if solicitud.menu_type:
                nombre_menu = solicitud.menu_type.nombre

                if nombre_menu in totales_menu:
                    totales_menu[nombre_menu] += 1

        resultado.append({
            "id": pedido.id,
            "sector_id": pedido.sector_id,
            "fecha": pedido.fecha.isoformat(),
            "estado": pedido.estado,
            "creado_por": pedido.creado_por,
            "totales": {
                "por_comida": totales_comida,
                "por_menu": totales_menu,
            },
        })

    return jsonify({
        "pedidos": resultado,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": total,
    }), 200


@pedidos_bp.route("/<int:request_id>", methods=["GET"])
def consultar_pedido(request_id):
    """Obtiene el detalle de un pedido."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado"
        }), 403

    usuario = _obtener_usuario_autenticado()

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido"
        }), 401

    if usuario.sector_id is None:
        return jsonify({
            "error": "El usuario no tiene un sector asignado"
        }), 403

    pedido = Pedido.query.get(request_id)

    if pedido is None:
        return jsonify({
            "error": "Pedido no encontrado"
        }), 404

    # Un Jefe de Servicio solo puede consultar pedidos de su sector.
    if pedido.sector_id != usuario.sector_id:
        return jsonify({
            "error": "No autorizado para consultar este pedido"
        }), 403

    sector = db.session.get(Sector, pedido.sector_id)

    solicitudes = (
        SolicitudPedido.query
        .filter_by(pedido_id=pedido.id)
        .all()
    )

    detalle = []

    # Totales por tipo de comida
    totales_comida = {
        "desayuno": {
            "solicitadas": 0,
            "autorizadas": 0
        },
        "almuerzo": {
            "solicitadas": 0,
            "autorizadas": 0
        },
        "merienda": {
            "solicitadas": 0,
            "autorizadas": 0
        },
        "cena": {
            "solicitadas": 0,
            "autorizadas": 0
        }
    }

    # Totales por tipo de menú
    totales_menu = {}

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
                "autorizadas": 0
            }

        totales_comida[nombre_comida]["solicitadas"] += 1

        if autorizada:
            totales_comida[nombre_comida]["autorizadas"] += 1

        if nombre_menu not in totales_menu:
            totales_menu[nombre_menu] = {
                "solicitadas": 0,
                "autorizadas": 0
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
                "apellido": solicitud.persona.apellido
            },
            "tipo_comida": {
                "id": solicitud.tipo_comida_id,
                "nombre": solicitud.food_type.nombre
            },
            "tipo_menu": {
                "id": solicitud.tipo_menu_id,
                "nombre": solicitud.menu_type.nombre
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
                )
            }
        })

    return jsonify({
        "id": pedido.id,
        "fecha": pedido.fecha.isoformat(),
        "estado": pedido.estado,
        "sector": {
            "id": pedido.sector_id,
            "nombre": sector.nombre if sector else None
        },
        "creado_por": pedido.creado_por,
        "totales": {
            "por_comida": totales_comida,
            "por_menu": totales_menu
        },
        "solicitudes": detalle
    }), 200


@pedidos_bp.route("/<int:request_id>", methods=["PUT"])
def modificar_pedido(request_id):
    """Modifica un pedido existente."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "El cuerpo de la solicitud es obligatorio",
        }), 400

    usuario = _obtener_usuario_autenticado()

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    if usuario.sector_id is None:
        return jsonify({
            "error": "El Jefe de Servicio no tiene un sector asignado",
        }), 403

    pedido = Pedido.query.get(request_id)

    if pedido is None:
        return jsonify({
            "error": "Pedido no encontrado",
        }), 404

    if pedido.sector_id != usuario.sector_id:
        return jsonify({
            "error": "No autorizado para modificar este pedido",
        }), 403

    if pedido.estado != "confirmado":
        return jsonify({
            "error": "Solo se pueden modificar pedidos confirmados",
        }), 409

    es_valido, resultado = validar_pedido(data)

    if not es_valido:
        return jsonify(resultado), 400

    if resultado["fecha_desde"] != resultado["fecha_hasta"]:
        return jsonify({
            "error": (
                "La modificación de pedidos con rango de fechas "
                "todavía no está implementada"
            ),
        }), 400

    nueva_fecha = resultado["fecha_desde"]

    pedido_existente = Pedido.query.filter(
        Pedido.sector_id == pedido.sector_id,
        Pedido.fecha == nueva_fecha,
        Pedido.id != pedido.id,
    ).first()

    if pedido_existente:
        return jsonify({
            "error": "Ya existe un pedido para ese sector y fecha",
            "request_id": pedido_existente.id,
        }), 409

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

    except ValueError as exc:
        db.session.rollback()

        return jsonify({
            "error": str(exc),
        }), 400

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "No se pudo modificar el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido modificado correctamente",
        "pedido": {
            "id": pedido.id,
            "sector_id": pedido.sector_id,
            "fecha": pedido.fecha.isoformat(),
            "estado": pedido.estado,
            "creado_por": pedido.creado_por,
            "solicitudes": [
                {
                    "id": solicitud.id,
                    "person_id": solicitud.person_id,
                    "tipo_comida_id": solicitud.tipo_comida_id,
                    "tipo_menu_id": solicitud.tipo_menu_id,
                    "condicion": solicitud.condicion,
                }
                for solicitud in pedido.solicitudes
            ],
        },
    }), 200

@pedidos_bp.route("/<int:request_id>", methods=["DELETE"])
def eliminar_pedido(request_id):
    """Elimina un pedido existente."""

    if session.get("role") != "Jefe de Servicio":
        return jsonify({
            "error": "No autorizado",
        }), 403

    usuario = _obtener_usuario_autenticado()

    if usuario is None or not usuario.activo:
        return jsonify({
            "error": "Usuario no válido",
        }), 401

    if usuario.sector_id is None:
        return jsonify({
            "error": "El Jefe de Servicio no tiene un sector asignado",
        }), 403

    pedido = Pedido.query.get(request_id)

    if pedido is None:
        return jsonify({
            "error": "Pedido no encontrado",
        }), 404

    if pedido.sector_id != usuario.sector_id:
        return jsonify({
            "error": "No autorizado para eliminar este pedido",
        }), 403

    if pedido.estado != "confirmado":
        return jsonify({
            "error": "Solo se pueden eliminar pedidos confirmados",
        }), 409
    try:
        solicitudes = SolicitudPedido.query.filter_by(
            pedido_id=pedido.id
        ).all()

        for solicitud in solicitudes:
            if solicitud.autorizacion is not None:
                db.session.delete(solicitud.autorizacion)

            db.session.delete(solicitud)

        db.session.delete(pedido)
        db.session.commit()

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "No se pudo eliminar el pedido",
        }), 500

    return jsonify({
        "mensaje": "Pedido eliminado correctamente",
        "request_id": request_id,
    }), 200