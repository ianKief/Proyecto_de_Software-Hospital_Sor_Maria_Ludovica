"""API del módulo de Entregas: comidas autorizadas y entregas."""
from flask import Blueprint, jsonify, request

from src.core.deliveries import (
    buscar_comidas_autorizadas,
    comidas_autorizadas_de,
    datos_comida_autorizada,
    datos_entrega,
    filtros_del_turno_actual,
    listar_entregas,
    obtener_entrega,
    registrar_entrega,
    resumen_entregas,
    resumen_entregas_por_periodo,
    totales_comidas_autorizadas,
    totales_resumen_entregas,
)
from src.core.deliveries.turnos import hoy
from src.core.paginacion import paginar
from src.web.helpers.api_auth import api_permission_required
from src.web.helpers.entregas_validaciones import (
    validar_entrega,
    validar_fecha_opcional,
    validar_filtros_comidas_autorizadas,
    validar_filtros_entregas,
    validar_filtros_resumen_periodo,
    validar_filtros_resumen_entregas,
)
from src.web.helpers.paginacion import respuesta_paginada, validar_pagina

# Prefijo "/api" para que las rutas queden /api/authorized-meals y
# /api/deliveries sin barra final.
api_deliveries_bp = Blueprint("api_deliveries", __name__, url_prefix="/api")


@api_deliveries_bp.get("/authorized-meals")
@api_permission_required("authorized_meals_index")
def authorized_meals_index():
    """Lista paginada de comidas autorizadas según los filtros del query string.

    Filtros: ``fecha`` (AAAA-MM-DD), ``dni``, ``nombre``, ``sector_id`` y
    ``tipo_comida_id``; hace falta al menos uno. Cada ítem trae la marca
    ``entregada`` y la respuesta suma ``totales`` (autorizadas y entregadas)
    calculados sobre todo el filtro, no solo sobre la página.
    Responde 400 si la página o algún filtro no es válido.
    """
    numero_pagina = validar_pagina(request.args.get("page"))

    if numero_pagina is None:
        return jsonify({
            "error": "El parámetro page no es válido",
            "campos": ["page"],
        }), 400

    es_valido, resultado = validar_filtros_comidas_autorizadas(request.args)

    if not es_valido:
        return jsonify(resultado), 400

    consulta = buscar_comidas_autorizadas(**resultado)
    pagina = paginar(consulta, numero_pagina)
    items = [datos_comida_autorizada(solicitud) for solicitud in pagina.items]

    cuerpo = respuesta_paginada(pagina, items)
    cuerpo["totales"] = totales_comidas_autorizadas(consulta)
    return jsonify(cuerpo), 200


@api_deliveries_bp.get("/authorized-meals/<int:person_id>")
@api_permission_required("authorized_meals_index")
def authorized_meals_show(person_id):
    """Comidas autorizadas de una persona en una fecha (por defecto, hoy).

    Responde 400 si la fecha no es válida y 404 si la persona no existe.
    No se pagina: una persona tiene pocas comidas por día.
    """
    es_valido, resultado = validar_fecha_opcional(request.args)

    if not es_valido:
        return jsonify(resultado), 400

    fecha = resultado or hoy()

    try:
        solicitudes = comidas_autorizadas_de(person_id, fecha)
    except LookupError as error:
        return jsonify({"error": str(error)}), 404

    return jsonify({
        "persona_id": person_id,
        "fecha": fecha.isoformat(),
        "items": [datos_comida_autorizada(solicitud) for solicitud in solicitudes],
    }), 200


@api_deliveries_bp.get("/deliveries")
@api_permission_required("delivery_index")
def deliveries_index():
    """Lista paginada de entregas según los filtros del query string.

    Filtros: ``fecha`` (AAAA-MM-DD), ``sector_id`` y ``tipo_comida_id``.
    Si no viene ninguno, lista las de hoy del turno en curso; fuera de
    horario, todas las de hoy. Responde 400 si la página o algún filtro
    no es válido.
    """
    numero_pagina = validar_pagina(request.args.get("page"))

    if numero_pagina is None:
        return jsonify({
            "error": "El parámetro page no es válido",
            "campos": ["page"],
        }), 400

    es_valido, resultado = validar_filtros_entregas(request.args)

    if not es_valido:
        return jsonify(resultado), 400

    if all(valor is None for valor in resultado.values()):
        resultado = filtros_del_turno_actual()

    pagina = paginar(listar_entregas(**resultado), numero_pagina)
    items = [datos_entrega(entrega) for entrega in pagina.items]

    return jsonify(respuesta_paginada(pagina, items)), 200


# Va antes de /deliveries/<int:delivery_id> solo para que se lea mejor:
# no chocan, porque el conversor int no acepta "summary".
@api_deliveries_bp.get("/deliveries/summary")
@api_permission_required("delivery_index")
def deliveries_summary():
    """Comidas autorizadas contra entregadas, por tipo de comida y de menú.

    Filtros: ``fecha`` (AAAA-MM-DD), ``sector_id`` y ``tipo_comida_id``.
    Si no viene la fecha se usa hoy, haya o no otros filtros, para no sumar
    todo el historial. No se pagina: son pocas filas agrupadas.
    Responde 400 si algún filtro no es válido o viene ``page``.
    """
    es_valido, resultado = validar_filtros_resumen_entregas(request.args)

    if not es_valido:
        return jsonify(resultado), 400

    if resultado["fecha"] is None:
        resultado["fecha"] = hoy()

    items = resumen_entregas(**resultado)

    return jsonify({
        "fecha": resultado["fecha"].isoformat(),
        "items": items,
        "totales": totales_resumen_entregas(items),
    }), 200


# Es parte de Resúmenes, pero va en este blueprint (prefijo "/api") para no
# tener que registrar otro en create_app ni tocar el de /api/summaries.
@api_deliveries_bp.get("/summaries/deliveries")
@api_permission_required("summary_deliveries")
def summary_deliveries():
    """Comidas autorizadas contra entregadas, agrupadas por período, sector, comida o menú.

    Usa los mismos parámetros que los otros ``/api/summaries/*``:
    ``fecha_desde``, ``fecha_hasta``, ``sector_id``, ``tipo_comida``,
    ``tipo_menu`` (nombres) y ``agrupamiento``; todos opcionales.
    Responde 400 si algún parámetro no es válido o la comida o el menú
    no existen.
    """
    es_valido, resultado = validar_filtros_resumen_periodo(request.args)

    if not es_valido:
        return jsonify(resultado), 400

    try:
        resultados = resumen_entregas_por_periodo(**resultado)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({
        "agrupamiento": resultado["agrupamiento"] or "total",
        "resultados": resultados,
        "totales": totales_resumen_entregas(resultados.values()),
    }), 200


@api_deliveries_bp.get("/deliveries/<int:delivery_id>")
@api_permission_required("delivery_show")
def deliveries_show(delivery_id):
    """Detalle de una entrega. Responde 404 si no existe."""
    try:
        entrega = obtener_entrega(delivery_id)
    except LookupError as error:
        return jsonify({"error": str(error)}), 404

    return jsonify(datos_entrega(entrega)), 200


@api_deliveries_bp.post("/deliveries")
@api_permission_required("delivery_new")
def deliveries_create(current_user):
    """Registra la entrega de una comida a una o varias personas.

    El cuerpo trae solo ``personas``, ``tipo_comida_id`` y ``responsable_id``:
    la fecha y la hora las pone el servidor y el usuario sale del token JWT.
    Responde 400 si el cuerpo no es JSON, no pasa la validación, está fuera
    del horario de la comida o alguna persona no tiene autorización; 409 si
    alguna persona ya retiró esa comida hoy; y 201 con la entrega registrada.
    """
    data = request.get_json(silent=True)

    # Se compara con None (y no "if not data") para que {} llegue al
    # validador y la respuesta diga qué campos faltan.
    if data is None:
        return jsonify({
            "error": "El cuerpo debe ser JSON válido",
            "campos": [],
        }), 400

    es_valido, resultado = validar_entrega(data)

    if not es_valido:
        return jsonify(resultado), 400

    # El decorador validó el token y pasa el usuario en current_user.
    try:
        entrega = registrar_entrega(resultado, current_user.id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 409

    return jsonify(datos_entrega(entrega)), 201
