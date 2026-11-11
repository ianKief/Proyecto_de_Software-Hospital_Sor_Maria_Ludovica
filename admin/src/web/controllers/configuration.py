"""Controlador de la pantalla de Ajustes (configuración general del sistema)."""
from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from sqlalchemy.exc import SQLAlchemyError

from src.core.configuration import obtener_configuracion, actualizar_configuracion
from src.web.helpers.auth import permission_required, check_permission
from src.web.helpers.configuracion_validaciones import (
    validar_configuracion,
    CAMPOS_PERMITIDOS,
    CAMPOS_HORARIOS,
    COMIDAS_EN_ORDEN,
    ELEMENTOS_MINIMO,
    ELEMENTOS_MAXIMO,
    LARGO_MAXIMO_MENSAJE,
)

configuration_bp = Blueprint("configuration", __name__, url_prefix="/configuration")


def _render_formulario(valores, errores=None, error_general=None, codigo=200):
    """Muestra el formulario de ajustes con los valores y errores indicados.

    ``valores`` es un diccionario con los campos de la configuración
    (los horarios como texto "HH:MM").
    ``errores`` relaciona cada campo con su mensaje de error, y
    ``error_general`` es un error que no corresponde a ningún campo.
    """
    return render_template(
        "configuration/configuration_form.html",
        valores=valores,
        errores=errores or {},
        error_general=error_general,
        puede_editar=check_permission("config_update"),
        elementos_minimo=ELEMENTOS_MINIMO,
        elementos_maximo=ELEMENTOS_MAXIMO,
        largo_maximo_mensaje=LARGO_MAXIMO_MENSAJE,
        comidas=COMIDAS_EN_ORDEN,
    ), codigo


def _formatear_hora(hora):
    """Devuelve la hora como "HH:MM", el formato que espera un <input type="time">."""
    return hora.strftime("%H:%M")


def _valores_guardados(configuracion):
    """Arma los valores a mostrar en el formulario a partir de la fila guardada."""
    return {
        "elementos_por_pagina": configuracion.elementos_por_pagina,
        "mantenimiento_activo": configuracion.mantenimiento_activo,
        "mensaje_mantenimiento": configuracion.mensaje_mantenimiento or "",
        "desayuno_inicio": _formatear_hora(configuracion.desayuno_inicio),
        "desayuno_fin": _formatear_hora(configuracion.desayuno_fin),
        "almuerzo_inicio": _formatear_hora(configuracion.almuerzo_inicio),
        "almuerzo_fin": _formatear_hora(configuracion.almuerzo_fin),
        "merienda_inicio": _formatear_hora(configuracion.merienda_inicio),
        "merienda_fin": _formatear_hora(configuracion.merienda_fin),
        "cena_inicio": _formatear_hora(configuracion.cena_inicio),
        "cena_fin": _formatear_hora(configuracion.cena_fin),
        "horario_corte": _formatear_hora(configuracion.horario_corte),
    }


def _valores_del_formulario():
    """Devuelve lo que escribió el usuario, para volver a mostrarlo si hay un error."""
    valores = {
        "elementos_por_pagina": request.form.get("elementos_por_pagina", ""),
        # Un checkbox destildado no se envía: si está en el form, estaba tildado.
        "mantenimiento_activo": "mantenimiento_activo" in request.form,
        "mensaje_mantenimiento": request.form.get("mensaje_mantenimiento", ""),
    }
    for campo in CAMPOS_HORARIOS:
        valores[campo] = request.form.get(campo, "")
    return valores


def campos_modificados(campos, valores_del_formulario, configuracion):
    """Devuelve, de ``campos``, los que el usuario cambió respecto de lo guardado.

    Sirve para los errores que involucran dos horarios (inicio >= fin o
    comidas superpuestas): el mensaje se muestra solo en el campo que el
    usuario tocó, que es el que probablemente tenga que corregir.
    Compara texto con texto: los horarios guardados se pasan a "HH:MM".

    Si no cambió ninguno o cambiaron todos, no hay uno solo para marcar
    y se devuelven todos los ``campos``.
    """
    guardados = _valores_guardados(configuracion)

    modificados = []
    for campo in campos:
        if valores_del_formulario[campo] != guardados[campo]:
            modificados.append(campo)

    if len(modificados) == 0 or len(modificados) == len(campos):
        return campos
    return modificados


@configuration_bp.get("/")
@permission_required("config_show")
def config_show():
    """Muestra el formulario de ajustes con los valores guardados."""
    configuracion = obtener_configuracion()
    return _render_formulario(_valores_guardados(configuracion))


@configuration_bp.post("/")
@permission_required("config_update")
def config_update():
    """Valida y guarda los ajustes enviados por el formulario.

    Si todo sale bien redirige a la pantalla de ajustes (así F5 no reenvía
    el formulario). Si hay errores, vuelve a mostrar el formulario con lo
    que escribió el usuario y el mensaje junto al campo.
    """
    es_valido, resultado = validar_configuracion(request.form.to_dict())

    if not es_valido:
        campos = resultado["campos"]
        if all(campo in CAMPOS_PERMITIDOS for campo in campos):
            valores = _valores_del_formulario()
            campos_a_marcar = campos_modificados(campos, valores, obtener_configuracion())
            errores = {campo: resultado["error"] for campo in campos_a_marcar}
            return _render_formulario(valores, errores=errores, codigo=422)
        # Campos extra: solo pasa con un pedido armado a mano, no hay campo donde mostrarlo.
        return _render_formulario(
            _valores_del_formulario(), error_general=resultado["error"], codigo=422
        )

    try:
        # El controlador lee la sesión y le pasa el usuario al núcleo para el log.
        actualizar_configuracion(resultado, session["user"])
    except SQLAlchemyError:
        # actualizar_configuracion ya hizo rollback y dejó el error en el log.
        return _render_formulario(
            _valores_del_formulario(),
            error_general="No se pudo guardar la configuración. Intentá de nuevo.",
            codigo=500,
        )

    flash("Configuración guardada.", "success")
    return redirect(url_for("configuration.config_show"))
