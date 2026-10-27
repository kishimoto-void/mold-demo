"""Typed errors for the Top Mold reference prototype."""

class TopMoldError(Exception):
    """Base class for errors safe to present to an operator."""

class IntakeError(TopMoldError):
    """A request-intake packet violates its declared contract."""

class PlanningError(TopMoldError):
    """A task or processor registry cannot be planned safely."""

class DialConfigError(TopMoldError):
    """Personalization settings or dial catalogs are invalid."""

class RegistryError(TopMoldError):
    """A registry violates its contract."""
