class SectorException(Exception):
    """Excepción base para el módulo de sectores."""
    pass


class SectorValidationError(SectorException):
    """Lanzada cuando fallan reglas de formato o datos básicos en el core."""
    pass


class SectorAlreadyExistsError(SectorException):
    """Lanzada cuando se intenta crear un sector con un nombre ya existente."""
    pass

class SectorInactiveExistsError(Exception):
    """Excepción lanzada cuando se intenta crear un sector que ya existe pero está inactivo."""
    pass