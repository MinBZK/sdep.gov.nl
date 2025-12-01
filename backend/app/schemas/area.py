"""Pydantic schemas for Area API responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AreaResponse(BaseModel):
    """Area response schema for STR areas."""

    model_config = ConfigDict(
        title="area.AreaResponse",
        from_attributes=True,
        populate_by_name=True,
    )

    area_id: str = Field(
        ...,
        alias="areaId",
        max_length=64,
        description="Area unique identifier (enables retrieval of area data)",
        examples=["amsterdam-area-0363"],
    )  # Attribute
    competent_authority_id: str = Field(
        ...,
        alias="competentAuthorityId",
        max_length=64,
        description="Competent authority id who submitted the area",
        examples=["0363"],
    )  # Attribute
    competent_authority_name: str = Field(
        ...,
        alias="competentAuthorityName",
        max_length=128,
        description="Competent authority name (for convenience)",
        examples=["Gemeente Amsterdam"],
    )  # Attribute
    filename: str = Field(
        ...,
        max_length=64,
        description="Area filename",
        examples=["Amsterdam.zip"],
    )  # Attribute
    created_at: datetime = Field(
        ...,
        alias="createdAt",
        description="Timestamp when the area was created",
        examples=["2025-01-15T10:30:00Z"],
    )  # Attribute


class AreasListResponse(BaseModel):
    """List of areas response schema."""

    model_config = ConfigDict(title="area.AreasListResponse")

    areas: list[AreaResponse] = Field(
        ...,
        description="List of areas in context of the current SDEP/member state",
    )


class AreasCountResponse(BaseModel):
    """Count of areas response schema."""

    model_config = ConfigDict(title="area.AreasCountResponse")

    count: int = Field(
        ...,
        ge=0,
        description="Total number of areas in context of the current SDEP/member state",
        examples=[42],
    )  # Attribute
