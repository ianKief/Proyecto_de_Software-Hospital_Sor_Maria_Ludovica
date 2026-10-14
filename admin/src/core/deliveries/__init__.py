"""Operaciones del módulo de Entregas."""
import logging
from collections import defaultdict
from datetime import timedelta, timezone

from sqlalchemy.exc import IntegrityError

from src.core.db import db
from src.core.deliveries.models import Entrega, EntregaDetalle
from src.core.deliveries.turnos import a_hora_argentina, ahora, hoy, turno_actual
from src.core.food_types.models import FoodType
from src.core.menu_types.models import MenuType
from src.core.pedidos.models import Autorizacion, Pedido, SolicitudPedido
from src.core.personnel.models import Personal
from src.core.sectors.models import Sector

logger = logging.getLogger(__name__)


def _consulta_autorizadas():
    """Consulta base de las solicitudes autorizadas.

    Una solicitud está autorizada si su pedido está en estado "autorizado"
    y su autorización individual tiene ``autorizada`` en True.
    Hace join con la persona para poder filtrar y ordenar por sus datos.
    """
    return (
        SolicitudPedido.query
        .join(SolicitudPedido.pedido)
        .join(SolicitudPedido.autorizacion)
        .join(SolicitudPedido.persona)
        .filter(Pedido.estado == "autorizado")
        .filter(Autorizacion.autorizada.is_(True))
    )


def buscar_comidas_autorizadas(
    fecha=None,
    dni=None,
    nombre=None,
    sector_id=None,
    tipo_comida_id=None,
):
    """Arma la consulta de comidas autorizadas con los filtros que vengan.

    - ``fecha``: fecha del pedido.
    - ``dni``: DNI exacto de la persona.
    - ``nombre``: texto parcial, sin distinguir mayúsculas, sobre "nombre apellido".
    - ``sector_id``: sector que hizo el pedido (no el sector actual de la persona).
    - ``tipo_comida_id``: tipo de comida de la solicitud.

    Las personas inactivas también aparecen. Devuelve la consulta sin
    ejecutar y con orden fijo, para pasarla a ``paginar()``.
    Que venga al menos un filtro lo controla el validador de la API.
    """
    consulta = _consulta_autorizadas()

    if fecha is not None:
        consulta = consulta.filter(Pedido.fecha == fecha)

    if dni:
        consulta = consulta.filter(Personal.dni == dni)

    if nombre:
        nombre_completo = Personal.nombre + " " + Personal.apellido
        consulta = consulta.filter(nombre_completo.ilike(f"%{nombre}%"))

    if sector_id is not None:
        consulta = consulta.filter(Pedido.sector_id == sector_id)

    if tipo_comida_id is not None:
        consulta = consulta.filter(
            SolicitudPedido.tipo_comida_id == tipo_comida_id
        )

    return consulta.order_by(
        Pedido.fecha,
        SolicitudPedido.tipo_comida_id,
        Personal.apellido,
        Personal.nombre,
        SolicitudPedido.id,
    )


def comidas_autorizadas_de(persona_id, fecha=None):
    """Devuelve la lista de solicitudes autorizadas de una persona en una fecha.

    Sin ``fecha`` usa la de hoy. Lanza ``LookupError`` si la persona no existe.
    """
    if db.session.get(Personal, persona_id) is None:
        raise LookupError("La persona no existe")

    if fecha is None:
        fecha = hoy()

    return (
        _consulta_autorizadas()
        .filter(SolicitudPedido.person_id == persona_id)
        .filter(Pedido.fecha == fecha)
        .order_by(SolicitudPedido.tipo_comida_id, SolicitudPedido.id)
        .all()
    )


def ya_entregada(persona_id, fecha, tipo_comida_id):
    """Indica si la persona ya retiró esa comida en esa fecha.

    Se controla por persona + fecha + comida, no por autorización: si la
    persona tiene dos autorizaciones (pedidas por dos sectores) y se entregó
    una, la otra también cuenta como entregada.
    """
    detalle = (
        EntregaDetalle.query
        .join(EntregaDetalle.autorizacion)
        .join(Autorizacion.solicitud)
        .join(SolicitudPedido.pedido)
        .filter(SolicitudPedido.person_id == persona_id)
        .filter(Pedido.fecha == fecha)
        .filter(SolicitudPedido.tipo_comida_id == tipo_comida_id)
        .first()
    )
    return detalle is not None


def datos_comida_autorizada(solicitud):
    """Arma el diccionario de una comida autorizada, listo para la API.

    El tipo de menú y la condición salen de la solicitud; el sector, del pedido.
    """
    pedido = solicitud.pedido
    persona = solicitud.persona
    # Pedido no tiene relación "sector" (issue #15): se busca por id.
    sector = db.session.get(Sector, pedido.sector_id)

    return {
        "autorizacion_id": solicitud.autorizacion.id,
        "fecha": pedido.fecha.isoformat(),
        "persona": {
            "id": persona.id,
            "dni": persona.dni,
            "nombre": persona.nombre,
            "apellido": persona.apellido,
            "activo": persona.activo,
        },
        "tipo_comida": {
            "id": solicitud.food_type.id,
            "nombre": solicitud.food_type.nombre,
        },
        "tipo_menu": {
            "id": solicitud.menu_type.id,
            "nombre": solicitud.menu_type.nombre,
        },
        "condicion": solicitud.condicion,
        "sector": {
            "id": sector.id,
            "nombre": sector.nombre,
        },
        "entregada": ya_entregada(
            persona.id,
            pedido.fecha,
            solicitud.tipo_comida_id,
        ),
    }


def totales_comidas_autorizadas(consulta):
    """Cuenta las comidas autorizadas de la consulta y cuántas ya se entregaron.

    Recibe la consulta de ``buscar_comidas_autorizadas`` (sin paginar), así los
    totales son de todo el filtro y no solo de una página.
    Se cuenta por autorización, igual que ``resumen_entregas``: una cuenta como
    entregada si tiene un detalle de entrega. Puede no coincidir con la marca
    "entregada" de cada ítem, que es por persona: si una persona tiene dos
    autorizaciones de la misma comida y retiró una, suma 2 autorizadas y 1 entregada.
    """
    entregadas = consulta.join(
        EntregaDetalle,
        EntregaDetalle.autorizacion_id == Autorizacion.id,
    )
    return {
        "autorizadas": consulta.count(),
        "entregadas": entregadas.count(),
    }


def _autorizacion_de_hoy(persona_id, fecha, tipo_comida_id):
    """Devuelve la autorización vigente de la persona para esa fecha y comida, o None.

    Si tiene dos (pedidas por dos sectores) devuelve la de menor id, así
    siempre se elige la misma y dos entregas simultáneas chocan en el UNIQUE.
    """
    solicitud = (
        _consulta_autorizadas()
        .filter(SolicitudPedido.person_id == persona_id)
        .filter(Pedido.fecha == fecha)
        .filter(SolicitudPedido.tipo_comida_id == tipo_comida_id)
        .order_by(Autorizacion.id)
        .first()
    )
    if solicitud is None:
        return None
    return solicitud.autorizacion


def registrar_entrega(datos, usuario_id):
    """Registra la entrega de una comida a una o varias personas y devuelve la Entrega.

    Recibe los datos ya validados por ``validar_entrega`` (``personas``,
    ``tipo_comida_id`` y ``responsable_id``) y el id del usuario del Comedor
    que la registra. La fecha y la hora las pone el servidor: ``created_at`` es
    el mismo momento con el que se controla el turno.

    Antes de crear nada controla todo; si algo falla no se guarda ninguna persona:
    - ``ValueError`` (400): comida o responsable inexistente, fuera del horario
      de esa comida, o alguna persona sin autorización para hoy.
    - ``RuntimeError`` (409): alguna persona ya retiró esa comida hoy.

    Las personas inactivas con la comida autorizada se entregan igual.
    """
    momento = ahora()
    fecha = momento.date()

    tipo_comida = db.session.get(FoodType, datos["tipo_comida_id"])
    if tipo_comida is None:
        raise ValueError("El tipo de comida no existe")

    if db.session.get(Personal, datos["responsable_id"]) is None:
        raise ValueError("El responsable del retiro no existe")

    if turno_actual(momento) != tipo_comida.nombre:
        raise ValueError(f"Fuera del horario de {tipo_comida.nombre}")

    # Se busca la autorización de cada persona; las que no tienen se juntan para avisar todas juntas.
    autorizaciones = []
    sin_autorizacion = []
    for persona_id in datos["personas"]:
        autorizacion = _autorizacion_de_hoy(persona_id, fecha, tipo_comida.id)
        if autorizacion is None:
            sin_autorizacion.append(persona_id)
        else:
            autorizaciones.append(autorizacion)

    if sin_autorizacion:
        raise ValueError(
            f"Sin autorización de {tipo_comida.nombre} para hoy: personas {sin_autorizacion}"
        )

    ya_retiraron = [
        persona_id
        for persona_id in datos["personas"]
        if ya_entregada(persona_id, fecha, tipo_comida.id)
    ]
    if ya_retiraron:
        raise RuntimeError(
            f"Ya retiraron {tipo_comida.nombre} hoy: personas {ya_retiraron}"
        )

    entrega = Entrega(
        # Se guarda el mismo momento con el que se validó el turno, en UTC y
        # sin zona como el default del modelo (issue #18).
        created_at=momento.astimezone(timezone.utc).replace(tzinfo=None),
        usuario_id=usuario_id,
        responsable_id=datos["responsable_id"],
        tipo_comida_id=tipo_comida.id,
        detalles=[
            EntregaDetalle(autorizacion_id=autorizacion.id)
            for autorizacion in autorizaciones
        ],
    )

    try:
        db.session.add(entrega)
        db.session.commit()
    except IntegrityError:
        # Otra entrega de la misma autorización se guardó entre el control y el commit.
        db.session.rollback()
        logger.warning("Entrega duplicada rechazada (usuario %s)", usuario_id)
        raise RuntimeError("Alguna de las personas ya retiró esta comida")
    except Exception:
        db.session.rollback()
        logger.exception("No se pudo registrar la entrega (usuario %s)", usuario_id)
        raise

    logger.info(
        "Entrega %s registrada por el usuario %s: %s para %s personas",
        entrega.id,
        usuario_id,
        tipo_comida.nombre,
        len(autorizaciones),
    )
    return entrega


def listar_entregas(fecha=None, sector_id=None, tipo_comida_id=None):
    """Arma la consulta de entregas con los filtros que vengan.

    - ``fecha``: fecha del pedido de las autorizaciones entregadas. No se usa
      ``created_at`` porque está en UTC: una cena a las 22 h quedaría al día siguiente.
    - ``sector_id``: sector que hizo el pedido de alguna de las personas.
    - ``tipo_comida_id``: tipo de comida de la entrega.

    La fecha y el sector están en el pedido (detalle → autorización → solicitud
    → pedido). Para que una entrega con personas de dos sectores no salga
    repetida, el join no se hace sobre ``Entrega``: se buscan los ids de las
    entregas que tienen algún detalle que cumple y se filtra con ``IN``.

    Devuelve la consulta sin ejecutar, con las más recientes primero, para
    pasarla a ``paginar()``.
    """
    consulta = Entrega.query

    if tipo_comida_id is not None:
        consulta = consulta.filter(Entrega.tipo_comida_id == tipo_comida_id)

    if fecha is not None or sector_id is not None:
        ids_entregas = (
            db.session.query(EntregaDetalle.entrega_id)
            .join(EntregaDetalle.autorizacion)
            .join(Autorizacion.solicitud)
            .join(SolicitudPedido.pedido)
        )
        if fecha is not None:
            ids_entregas = ids_entregas.filter(Pedido.fecha == fecha)
        if sector_id is not None:
            ids_entregas = ids_entregas.filter(Pedido.sector_id == sector_id)
        consulta = consulta.filter(Entrega.id.in_(ids_entregas))

    return consulta.order_by(Entrega.created_at.desc(), Entrega.id.desc())


def filtros_del_turno_actual():
    """Devuelve los filtros de ``listar_entregas`` para "lo que se está entregando ahora".

    La fecha es la de hoy y la comida, la del turno en curso (E1b). Si en
    este momento no hay turno (o esa comida no está cargada en la base),
    ``tipo_comida_id`` queda en ``None`` y se listan todas las comidas de hoy.
    Toma la hora de ``ahora()``, igual que ``registrar_entrega``.
    """
    momento = ahora()
    tipo_comida_id = None

    nombre_turno = turno_actual(momento)
    if nombre_turno is not None:
        tipo_comida = FoodType.query.filter_by(nombre=nombre_turno).first()
        if tipo_comida is not None:
            tipo_comida_id = tipo_comida.id

    return {
        "fecha": momento.date(),
        "sector_id": None,
        "tipo_comida_id": tipo_comida_id,
    }


def obtener_entrega(entrega_id):
    """Devuelve la entrega con ese id. Lanza ``LookupError`` si no existe."""
    entrega = db.session.get(Entrega, entrega_id)
    if entrega is None:
        raise LookupError("La entrega no existe")
    return entrega


def datos_entrega(entrega):
    """Arma el diccionario de una entrega, listo para la API.

    El tipo de menú, la condición y el sector de cada persona salen de su
    solicitud autorizada (detalle → autorización → solicitud).
    """
    personas = []
    for detalle in entrega.detalles:
        solicitud = detalle.autorizacion.solicitud
        persona = solicitud.persona
        # Pedido no tiene relación "sector" (issue #15): se busca por id.
        sector = db.session.get(Sector, solicitud.pedido.sector_id)
        personas.append({
            "id": persona.id,
            "dni": persona.dni,
            "nombre": persona.nombre,
            "apellido": persona.apellido,
            "tipo_menu": {
                "id": solicitud.menu_type.id,
                "nombre": solicitud.menu_type.nombre,
            },
            "condicion": solicitud.condicion,
            "sector": {
                "id": sector.id,
                "nombre": sector.nombre,
            },
        })

    return {
        "id": entrega.id,
        "fecha_hora": a_hora_argentina(entrega.created_at).isoformat(),
        "usuario": {
            "id": entrega.usuario.id,
            "email": entrega.usuario.email,
        },
        "responsable": {
            "id": entrega.responsable.id,
            "dni": entrega.responsable.dni,
            "nombre": entrega.responsable.nombre,
            "apellido": entrega.responsable.apellido,
        },
        "tipo_comida": {
            "id": entrega.tipo_comida.id,
            "nombre": entrega.tipo_comida.nombre,
        },
        "personas": personas,
    }


def resumen_entregas(fecha=None, tipo_comida_id=None, sector_id=None):
    """Cuenta las comidas autorizadas y las entregadas, por tipo de comida y de menú.

    Las autorizadas son las mismas filas que devuelve ``buscar_comidas_autorizadas``
    con esos filtros. Una autorizada cuenta como entregada si tiene un detalle
    de entrega. Se cuenta por autorización (no por persona como la marca
    "entregada" de E4): si una persona tiene dos autorizaciones de la misma
    comida y retiró una, suma 2 autorizadas y 1 entregada.

    Que venga al menos la fecha o el tipo de comida lo controla el endpoint.
    Devuelve una lista ordenada por comida y menú.
    """
    filas = (
        buscar_comidas_autorizadas(
            fecha=fecha,
            sector_id=sector_id,
            tipo_comida_id=tipo_comida_id,
        )
        .outerjoin(
            EntregaDetalle,
            EntregaDetalle.autorizacion_id == Autorizacion.id,
        )
        .add_columns(EntregaDetalle.id)
        .all()
    )

    totales = defaultdict(lambda: {"autorizadas": 0, "entregadas": 0})
    for solicitud, detalle_id in filas:
        clave = (solicitud.food_type.nombre, solicitud.menu_type.nombre)
        totales[clave]["autorizadas"] += 1
        if detalle_id is not None:
            totales[clave]["entregadas"] += 1

    resumen = []
    for (comida, menu), cantidades in sorted(totales.items()):
        resumen.append({
            "tipo_comida": comida,
            "tipo_menu": menu,
            "autorizadas": cantidades["autorizadas"],
            "entregadas": cantidades["entregadas"],
            "diferencia": cantidades["autorizadas"] - cantidades["entregadas"],
        })
    return resumen


def totales_resumen_entregas(resumen):
    """Suma las filas que devuelve ``resumen_entregas``.

    Devuelve un diccionario con ``autorizadas``, ``entregadas`` y
    ``diferencia``. Si el resumen está vacío, los tres valen 0.
    """
    autorizadas = sum(fila["autorizadas"] for fila in resumen)
    entregadas = sum(fila["entregadas"] for fila in resumen)
    return {
        "autorizadas": autorizadas,
        "entregadas": entregadas,
        "diferencia": autorizadas - entregadas,
    }


def _clave_de_grupo(solicitud, agrupamiento):
    """Devuelve la clave del grupo al que pertenece la solicitud.

    Son las mismas claves que usan los otros ``/api/summaries/*``: día
    ``AAAA-MM-DD``, semana (el lunes, ``AAAA-MM-DD``), mes ``AAAA-MM``,
    id del sector como texto, o el nombre de la comida o del menú.
    Sin agrupamiento, todo cae en ``"total"``.
    """
    fecha = solicitud.pedido.fecha

    if agrupamiento == "dia":
        return fecha.isoformat()
    if agrupamiento == "semana":
        lunes = fecha - timedelta(days=fecha.weekday())
        return lunes.isoformat()
    if agrupamiento == "mes":
        return fecha.strftime("%Y-%m")
    if agrupamiento == "sector":
        return str(solicitud.pedido.sector_id)
    if agrupamiento == "comida":
        return solicitud.food_type.nombre
    if agrupamiento == "menu":
        return solicitud.menu_type.nombre
    return "total"


def resumen_entregas_por_periodo(
    fecha_desde=None,
    fecha_hasta=None,
    sector_id=None,
    tipo_comida=None,
    tipo_menu=None,
    agrupamiento=None,
):
    """Cuenta las comidas autorizadas y las entregadas, agrupadas según ``agrupamiento``.

    Recibe los filtros ya validados por ``validar_filtros_resumen_periodo``.
    Las fechas son las del pedido (no ``created_at`` de la entrega, que
    está en UTC). ``tipo_comida`` y ``tipo_menu`` son nombres, sin
    distinguir mayúsculas; si no existen lanza ``ValueError`` (400).
    Se cuenta por autorización, igual que ``resumen_entregas``.

    Devuelve un diccionario ``clave -> {"autorizadas", "entregadas",
    "diferencia"}``; vacío si no hay comidas autorizadas.
    """
    consulta = _consulta_autorizadas()

    if fecha_desde is not None:
        consulta = consulta.filter(Pedido.fecha >= fecha_desde)

    if fecha_hasta is not None:
        consulta = consulta.filter(Pedido.fecha <= fecha_hasta)

    if sector_id is not None:
        consulta = consulta.filter(Pedido.sector_id == sector_id)

    if tipo_comida is not None:
        comida = FoodType.query.filter(
            db.func.lower(FoodType.nombre) == tipo_comida.lower()
        ).first()
        if comida is None:
            raise ValueError("El tipo de comida no existe")
        consulta = consulta.filter(SolicitudPedido.tipo_comida_id == comida.id)

    if tipo_menu is not None:
        menu = MenuType.query.filter(
            db.func.lower(MenuType.nombre) == tipo_menu.lower()
        ).first()
        if menu is None:
            raise ValueError("El tipo de menú no existe")
        # Se filtra por solicitud: cada persona tiene su tipo de menú.
        consulta = consulta.filter(SolicitudPedido.tipo_menu_id == menu.id)

    filas = (
        consulta
        .outerjoin(
            EntregaDetalle,
            EntregaDetalle.autorizacion_id == Autorizacion.id,
        )
        .add_columns(EntregaDetalle.id)
        .all()
    )

    resultados = defaultdict(lambda: {"autorizadas": 0, "entregadas": 0})
    for solicitud, detalle_id in filas:
        clave = _clave_de_grupo(solicitud, agrupamiento)
        resultados[clave]["autorizadas"] += 1
        if detalle_id is not None:
            resultados[clave]["entregadas"] += 1

    for cantidades in resultados.values():
        cantidades["diferencia"] = (
            cantidades["autorizadas"] - cantidades["entregadas"]
        )

    return dict(resultados)
