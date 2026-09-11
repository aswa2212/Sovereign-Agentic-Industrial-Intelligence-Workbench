"""Exceptions for Phase 11 Audit and Sovereignty subsystem."""


class AuditError(Exception):
    """Base exception for audit-related failures."""
    pass


class AuditStorageError(AuditError):
    """Raised when an error occurs while writing or reading audit events."""
    pass


class AuditIntegrityError(AuditError):
    """Raised when audit chain validation detects corruption or tampering."""
    pass


class SovereigntyViolationError(AuditError):
    """Raised when sovereign or air-gap configuration constraints are breached."""
    pass
