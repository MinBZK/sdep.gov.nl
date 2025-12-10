"""Pydantic schemas for Activity API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator


def validate_year_ge_2025(v: datetime) -> datetime:
    """Validate that datetime year is >= 2025."""
    if v.year < 2025:
        raise ValueError("Start datetime year must be >= 2025")
    return v


class AddressRequest(BaseModel):
    """Address composite schema for activity requests.

    Validation Layer:
    - All syntax validation (lengths, types, constraints) happens here
    - Service layer receives validated data
    """

    model_config = ConfigDict(
        title="activity.AddressRequest",
        populate_by_name=True,  # Allow both snake_case and camelCase
    )

    street: str = Field(
        ...,
        max_length=64,
        description="Street name",
        examples=["Prinsengracht"],
    )  # Attribute

    number: int = Field(
        ...,
        ge=1,
        description="House number",
        examples=[263],
    )  # Attribute

    letter: str | None = Field(
        None,
        max_length=1,
        description="House letter (optional)",
        examples=["a"],
    )  # Attribute

    addition: str | None = Field(
        None,
        max_length=10,
        description="House addition (optional)",
        examples=["5h"],
    )  # Attribute

    postal_code: str = Field(
        ...,
        alias="postalCode",
        min_length=1,
        max_length=8,
        pattern=r"^[0-9A-Za-z]+$",
        description="Postal code (no spaces, alphanumeric)",
        examples=["1016HV"],
    )  # Attribute

    city: str = Field(
        ...,
        max_length=64,
        description="City name",
        examples=["Amsterdam"],
    )  # Attribute

    @field_validator("letter")
    @classmethod
    def validate_letter_is_alphabetic(cls, v: str | None) -> str | None:
        """Validate letter contains only alphabetic characters."""
        if v is not None and not v.isalpha():
            raise ValueError("Letter must contain only alphabetic characters")
        return v

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code_format(cls, v: str) -> str:
        """Validate postal code has no spaces and is alphanumeric."""
        if " " in v:
            raise ValueError("Postal code must not contain spaces")
        if not v.isalnum():
            raise ValueError("Postal code must be alphanumeric")
        return v


class TemporalRequest(BaseModel):
    """Temporal composite schema for activity requests.

    Validation Layer:
    - Validates datetime formats
    - Ensures start year is >= 2025
    - Ensures start is before end
    """

    model_config = ConfigDict(
        title="activity.TemporalRequest",
        populate_by_name=True,
    )

    start_date_time: Annotated[datetime, AfterValidator(validate_year_ge_2025)] = Field(
        ...,
        alias="startDatetime",
        description="Start date and time of the rental activity (year must be >= 2025)",
        examples=["2025-06-01T14:00:00Z"],
    )  # Attribute

    end_date_time: datetime = Field(
        ...,
        alias="endDatetime",
        description="End date and time of the rental activity (must be after startDatetime)",
        examples=["2025-06-07T11:00:00Z"],
    )  # Attribute

    @field_validator("end_date_time")
    @classmethod
    def validate_end_after_start(cls, v: datetime, info) -> datetime:
        """Validate end datetime is after start datetime."""
        if "start_date_time" in info.data and v <= info.data["start_date_time"]:
            raise ValueError("End datetime must be after start datetime")
        return v


class MetaDataRequest(BaseModel):
    """Metadata schema for activity batch submissions.

    Contains metadata that applies to all activities in a batch submission.
    Platform ID and name are now extracted from the JWT token (client_id and client_name claims).

    Note: This is kept as a placeholder for future batch-level metadata.
    Currently, no batch-level fields are required.
    """

    model_config = ConfigDict(
        title="activity.MetaDataRequest",
        populate_by_name=True,
    )


class ActivityRequest(BaseModel):
    """Activity request schema for creating rental activities.

    Validation Layer:
    - Validates all syntax constraints (lengths, ranges, types)
    - Converts camelCase (API) to snake_case (internal Python)

    Constraints:
    - Unique constraint: { url, temporal.startDatetime, temporal.endDatetime }
      (enforced at database level, returns 409 Conflict on violation)
    """

    model_config = ConfigDict(
        title="activity.ActivityRequest",
        populate_by_name=True,  # Allow both snake_case and camelCase
    )

    url: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique URL of the advertisement",
        examples=["http://example.com/amsterdam-myhouse-1"],
    )  # Attribute

    address: AddressRequest = Field(
        ...,
        description="Address composite containing street, number, postal code, and city",
    )  # Composite

    registration_number: str = Field(
        ...,
        alias="registrationNumber",
        min_length=1,
        max_length=32,
        description="Registration number for the address",
        examples=["REG0001"],
    )  # Attribute

    area_id: str = Field(
        ...,
        alias="areaId",
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9-]+$",
        description="Area identifier string (lowercase alphanumeric with dashes)",
        examples=["amsterdam-area-0363"],
    )  # Attribute

    @field_validator("area_id")
    @classmethod
    def validate_area_id_alphanumeric(cls, v: str) -> str:
        """Validate area_id is lowercase alphanumeric with dashes."""
        allowed_chars = set("0123456789abcdefghijklmnopqrstuvwxyz-")
        if not all(c in allowed_chars for c in v):
            raise ValueError(
                "Area ID must contain only lowercase alphanumeric characters and dashes"
            )
        return v

    number_of_guests: int = Field(
        ...,
        alias="numberOfGuests",
        ge=1,
        le=1024,
        description="Number of guests",
        examples=[4],
    )  # Attribute

    country_of_guests: list[str] = Field(
        ...,
        alias="countryOfGuests",
        min_length=1,
        max_length=1024,
        description="Array of country codes of guests (ISO 3166-1 alpha-3: exactly 3 uppercase letters per code)",
        examples=[["NLD", "DEU", "BEL"]],
    )  # Attribute

    @field_validator("country_of_guests")
    @classmethod
    def validate_country_codes(cls, v: list[str]) -> list[str]:
        """Validate country codes are ISO 3166-1 alpha-3 (exactly 3 uppercase letters)."""
        for country_code in v:
            if len(country_code) != 3:
                raise ValueError(
                    f"Country code '{country_code}' must be exactly 3 characters (ISO 3166-1 alpha-3)"
                )
            if not country_code.isupper() or not country_code.isalpha():
                raise ValueError(
                    f"Country code '{country_code}' must be uppercase alphabetic characters"
                )
        return v

    temporal: TemporalRequest = Field(
        ...,
        description="Temporal composite containing start and end date/time",
    )  # Composite

    def to_service_dict(self, platform_id: str, platform_name: str) -> dict:
        """
        Convert Pydantic model to dictionary for service layer.

        Normalizes metadata (platform) from batch level to each activity.
        Flattens nested composites (address, temporal) to match service layer expectations.
        Converts all field names to snake_case.

        Args:
            platform_id: Platform ID string from JWT token (client_id claim)
            platform_name: Platform name from JWT token (client_name claim)

        Returns:
            Dictionary with snake_case keys and flattened structure
        """
        return {
            "url": self.url,
            "registration_number": self.registration_number,
            "platform_id_str": platform_id,
            "platform_name": platform_name,
            "address_street": self.address.street,
            "address_number": self.address.number,
            "address_letter": self.address.letter,
            "address_addition": self.address.addition,
            "address_postal_code": self.address.postal_code,
            "address_city": self.address.city,
            "temporal_start_date_time": self.temporal.start_date_time,
            "temporal_end_date_time": self.temporal.end_date_time,
            "area_id": self.area_id,
            "country_of_guests": self.country_of_guests,
            "number_of_guests": self.number_of_guests,
        }


class ActivityListRequest(BaseModel):
    """List of activities for bulk submission.

    Validation Layer:
    - Validates the entire list
    - Each activity is validated individually
    - Platform (from token) is normalized to each activity in to_service_list()
    """

    model_config = ConfigDict(title="activity.ActivityListRequest")

    metadata: MetaDataRequest = Field(
        ...,
        description="Metadata that applies to all activities in this batch (placeholder for future use)",
    )

    activities: list[ActivityRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of activities to process (max 100 per batch)",
    )

    def to_service_list(self, platform_id: str, platform_name: str) -> list[dict]:
        """
        Convert list of Pydantic models to list of dictionaries for service layer.

        Normalizes platform (from JWT token) from batch level to each activity.
        This happens at the API layer to keep service layer focused on business logic.

        Args:
            platform_id: Platform ID string extracted from JWT token (client_id claim)
            platform_name: Platform name extracted from JWT token (client_name claim)

        Returns:
            List of dictionaries with flattened structure, each containing normalized metadata
        """
        return [
            activity.to_service_dict(
                platform_id=platform_id, platform_name=platform_name
            )
            for activity in self.activities
        ]


class AddressResponse(BaseModel):
    """Address composite schema for activity responses."""

    model_config = ConfigDict(
        title="activity.AddressResponse",
        populate_by_name=True,
    )

    street: str = Field(..., description="Street name")  # Attribute
    number: int = Field(..., description="House number")  # Attribute
    letter: str | None = Field(None, description="House letter (optional)")  # Attribute
    addition: str | None = Field(
        None, description="House addition (optional)"
    )  # Attribute
    postalCode: str = Field(
        ..., alias="postalCode", description="Postal code"
    )  # Attribute
    city: str = Field(..., description="City name")  # Attribute


class TemporalResponse(BaseModel):
    """Temporal composite schema for activity responses."""

    model_config = ConfigDict(
        title="activity.TemporalResponse",
        populate_by_name=True,
    )

    startDatetime: datetime = Field(
        ...,
        alias="startDatetime",
        description="Start date and time of the rental activity",
    )  # Attribute
    endDatetime: datetime = Field(
        ..., alias="endDatetime", description="End date and time of the rental activity"
    )  # Attribute


class ActivityResponse(BaseModel):
    """Activity response schema."""

    model_config = ConfigDict(
        title="activity.ActivityResponse",
        from_attributes=True,
        populate_by_name=True,
    )

    activity_id: str = Field(
        ..., alias="activityId", description="Activity identifier"
    )  # Attribute - response only
    platformId: str = Field(
        ..., alias="platformId", description="Platform ID"
    )  # Attribute
    platformName: str = Field(
        ..., alias="platformName", description="Platform name"
    )  # Attribute
    areaId: str = Field(
        ..., alias="areaId", description="Area ID"
    )  # Reference - foreign key to Area
    url: str = Field(..., description="URL of the advertisement")  # Attribute
    address: AddressResponse = Field(..., description="Address composite")  # Composite
    registrationNumber: str = Field(
        ...,
        alias="registrationNumber",
        description="Registration number for the address",
    )  # Attribute
    numberOfGuests: int = Field(
        ..., alias="numberOfGuests", description="Number of guests"
    )  # Attribute
    countryOfGuests: list[str] = Field(
        ..., alias="countryOfGuests", description="Array of country codes of guests"
    )  # Attribute
    temporal: TemporalResponse = Field(
        ..., description="Temporal composite"
    )  # Composite
    createdAt: datetime = Field(
        ..., alias="createdAt", description="Creation timestamp"
    )  # Attribute


class ActivityListResponse(BaseModel):
    """List of activities for GET responses."""

    model_config = ConfigDict(title="activity.ActivityListResponse")

    activities: list[ActivityResponse] = Field(
        ..., description="List of activities"
    )


class ActivityCountResponse(BaseModel):
    """Count of activities response schema."""

    model_config = ConfigDict(title="activity.ActivityCountResponse")

    count: int = Field(
        ...,
        ge=0,
        description="Total number of activity records",
        examples=[42],
    )  # Attribute
