from datetime import date, timedelta

from src.core.db import db
from src.core.personnel.models import AsignacionSector, Personal
from src.core.sectors.models import Sector


def cambiar_asignacion_sector(personal_id, sector_id, fecha_desde=None):
    """Cambia el sector de una persona conservando su historial."""

    if fecha_desde is None:
        fecha_desde = date.today()

    personal = db.session.get(Personal, personal_id)

    if personal is None:
        raise LookupError("Personal no encontrado")

    nuevo_sector = None

    if sector_id is not None:
        nuevo_sector = db.session.get(Sector, sector_id)

        if nuevo_sector is None:
            raise LookupError("Sector no encontrado")

        if not nuevo_sector.activo:
            raise ValueError("No se puede asignar personal a un sector inactivo")

    asignacion_actual = (
        AsignacionSector.query
        .filter_by(
            personal_id=personal.id,
            fecha_hasta=None,
        )
        .first()
    )

    if (
        asignacion_actual is not None
        and asignacion_actual.sector_id == sector_id
    ):
        return personal

    try:
        if asignacion_actual is not None:
            if fecha_desde < asignacion_actual.fecha_desde:
                raise ValueError(
                    "La fecha del cambio no puede ser anterior "
                    "al inicio de la asignación vigente"
                )

            asignacion_actual.fecha_hasta = max(
                fecha_desde - timedelta(days=1),
                asignacion_actual.fecha_desde,
            )

        personal.sector_id = sector_id

        if nuevo_sector is not None:
            nueva_asignacion = AsignacionSector(
                personal_id=personal.id,
                sector_id=nuevo_sector.id,
                fecha_desde=fecha_desde,
            )
            db.session.add(nueva_asignacion)

        db.session.commit()
        return personal

    except Exception:
        db.session.rollback()
        raise