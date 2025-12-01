"""Validation error schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ValidationError(BaseModel):
    """Validation error detail schema"""

    model_config = ConfigDict(title="validation.ValidationError")

    loc: list[str | int] = Field(
        ...,
        description="Error location in the request",
        examples=[["body", "address", "postalCode"]],
    )
    msg: str = Field(
        ...,
        description="Error message",
        examples=["String should have at most 8 characters"],
    )
    type: str = Field(
        ...,
        description="Error type",
        examples=["string_too_long"],
    )


class HTTPValidationError(BaseModel):
    """HTTP validation error response schema"""

    model_config = ConfigDict(title="validation.HTTPValidationError")

    detail: list[ValidationError] = Field(..., description="List of validation errors")
