from typing import Any


class MnemosError(Exception):
    """Base exception for all Mnemos errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(MnemosError):
    """Raised when API key is missing or invalid."""
    pass


class TenantNotFoundError(MnemosError):
    """Raised when a tenant is not found."""
    pass


class EntityNotFoundError(MnemosError):
    """Raised when an entity is not found."""
    pass


class MemoryNotFoundError(MnemosError):
    """Raised when a memory unit is not found."""
    pass


class TemporalConflictError(MnemosError):
    """Raised when an irreconcilable temporal conflict is detected."""
    pass


class GraphCycleError(MnemosError):
    """Raised when graph traversal encounters an illegal cyclic state."""
    pass


class ValidationError(MnemosError):
    """Raised when input validation fails."""
    pass
