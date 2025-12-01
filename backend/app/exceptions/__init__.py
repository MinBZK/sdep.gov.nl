"""Custom exceptions for the SDEP application."""

from .auth import AuthenticationError, AuthorizationError, InvalidTokenError
from .base import SDEPError
from .business import (
    BusinessLogicError,
    DuplicateResourceError,
    InvalidOperationError,
    ResourceNotFoundError,
)
from .validation import DataValidationError, FileValidationError, ValidationError

__all__ = [
    # Base
    "SDEPError",
    # Business
    "BusinessLogicError",
    "ResourceNotFoundError",
    "DuplicateResourceError",
    "InvalidOperationError",
    # Validation
    "ValidationError",
    "FileValidationError",
    "DataValidationError",
    # Auth
    "AuthenticationError",
    "AuthorizationError",
    "InvalidTokenError",
]
