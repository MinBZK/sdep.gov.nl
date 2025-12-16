"""Centralized exception handler registration for FastAPI apps."""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    InvalidTokenError,
    ResourceNotFoundError,
    ValidationError,
)
from app.exceptions.handlers import (
    app_validation_exception_handler,
    authentication_exception_handler,
    authorization_exception_handler,
    business_logic_exception_handler,
    general_exception_handler,
    http_exception_handler,
    resource_not_found_exception_handler,
    validation_exception_handler,
)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers for the application.

    Order matters: more specific handlers should be registered before general ones.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, app_validation_exception_handler)
    app.add_exception_handler(BusinessLogicError, business_logic_exception_handler)
    app.add_exception_handler(
        ResourceNotFoundError, resource_not_found_exception_handler
    )
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.add_exception_handler(AuthorizationError, authorization_exception_handler)
    app.add_exception_handler(InvalidTokenError, authentication_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


__all__ = ["register_exception_handlers"]
