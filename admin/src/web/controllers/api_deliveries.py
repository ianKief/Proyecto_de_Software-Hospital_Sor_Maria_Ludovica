"""API del módulo de Entregas: comidas autorizadas y entregas."""
from flask import Blueprint, jsonify, request, session

from src.core.deliveries import (
    buscar_comidas_autorizadas,
    comidas_autorizadas_de,
    datos_comida_autorizada,
    datos_entrega,
    registrar_entrega,
    totales_comidas_autorizadas,
)
from src.core.deliveries.turnos import hoy
from src.core.paginacion import paginar
from src.web.helpers.api_auth import api_permission_required
from src.web.helpers.entregas_validaciones import (
    validar_entrega,
    validar_fecha_opcional,
    validar_filtros_comidas_autorizadas,
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


@api_deliveries_bp.post("/deliveries")
@api_permission_required("delivery_new")
def deliveries_create():
    """Registra la entrega de una comida a una o varias personas.

    El cuerpo trae solo ``personas``, ``tipo_comida_id`` y ``responsable_id``:
    la fecha y la hora las pone el servidor y el usuario sale de la sesión.
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

    # El decorador ya garantizó que hay sesión iniciada.
    try:
        entrega = registrar_entrega(resultado, session["user_id"])
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 409

    return jsonify(datos_entrega(entrega)), 201
