"""Pydantic schemas for Activity API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_serializer


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
    - Date-only submissions are permitted, and will be stored internally using a 00:00:00 timestamp
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


class ActivityRequest(BaseModel):
    """Activity request schema for creating rental activities.

    Platform:
    - NOT in request payload (extracted from JWT token at API layer)
    - PlatformId comes from token's client_id claim
    - PlatformName comes from token's client_name claim
    - Will be auto-created if it doesn't exist yet

    Activity ID:
    - Optional: If not provided, will be auto-generated (RFC 9562 UUID)

    Activity Name:
    - Optional: Human-readable name (max 128 chars)

    Validation Layer:
    - Validates all syntax constraints (lengths, ranges, types)

    Constraints (enforced at database level):
    - Unique constraint: (activityId, createdAt) for versioning support
    """

    model_config = ConfigDict(
        title="activity.ActivityRequest",
        populate_by_name=True,  # Allow both snake_case and camelCase
    )

    activity_id: str | None = Field(
        None,
        alias="activityId",
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9-]+$",
        description="Activity functional ID (optional, auto-generated UUID if not provided; lowercase alphanumeric with hyphens, max 64 chars)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )  # Functional ID

    activity_name: str | None = Field(
        None,
        alias="activityName",
        max_length=64,
        description="Activity name (optional, human-readable, max 64 chars)",
        examples=["Amsterdam Summer Rental"],
    )  # Functional name

    area_id: str = Field(
        ...,
        alias="areaId",
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9-]+$",
        description="Area functional ID (lowercase alphanumeric with hyphens, max 64 chars)",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )  # Functional ID reference

    url: str | None = Field(
        None,
        min_length=1,
        max_length=128,
        description="Unique URL of the advertisement (optional)",
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

    number_of_guests: int | None = Field(
        None,
        alias="numberOfGuests",
        ge=1,
        le=1024,
        description="Number of guests (optional, 1-1024 when provided)",
        examples=[4],
    )  # Attribute

    country_of_guests: list[str] | None = Field(
        None,
        alias="countryOfGuests",
        max_length=1024,
        description="Array of country codes of guests (optional, ISO 3166-1 alpha-3: exactly 3 uppercase letters per code, 1-1024 when provided)",
        examples=[["NLD", "DEU", "BEL"]],
    )  # Attribute

    @field_validator("country_of_guests")
    @classmethod
    def validate_country_codes(cls, v: list[str] | None) -> list[str] | None:
        """Validate country codes are ISO 3166-1 alpha-3 (exactly 3 uppercase letters)."""
        if v is None:
            return v
        if len(v) < 1:
            raise ValueError("Country codes list must contain at least 1 item when provided")
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
            "platform_id_str": platform_id,
            "platform_name": platform_name,
            "activity_id": self.activity_id,
            "activity_name": self.activity_name,
            "url": self.url,
            "registration_number": self.registration_number,
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

    activities: list[ActivityRequest] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of activities to process (max 1000 per batch)",
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
        ...,
        alias="activityId",
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9-]+$",
        description="Activity functional ID (lowercase alphanumeric with hyphens, max 64 chars)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )  # Functional ID
    activity_name: str | None = Field(
        None,
        alias="activityName",
        max_length=64,
        description="Activity name (optional, max 64 chars)",
    )  # Functional name
    created_at: datetime = Field(
        ..., alias="createdAt", description="Creation timestamp"
    )  # Attribute
    platform_id: str = Field(
        ...,
        alias="platformId",
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9-]+$",
        description="Platform functional ID (lowercase alphanumeric with hyphens, max 64 chars)"
    )  # Attribute
    platform_name: str | None = Field(
        None,
        alias="platformName",
        max_length=64,
        description="Platform name (optional, max 64 chars)",
    )  # Attribute
    area_id: str = Field(
        ...,
        alias="areaId",
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9-]+$",
        description="Area functional ID (lowercase alphanumeric with hyphens, max 64 chars)"
    )  # Functional ID reference
    url: str | None = Field(None, description="URL of the advertisement (optional)")  # Attribute
    address: AddressResponse = Field(..., description="Address composite")  # Composite
    registration_number: str = Field(
        ...,
        alias="registrationNumber",
        description="Registration number for the address",
    )  # Attribute
    number_of_guests: int | None = Field(
        None, alias="numberOfGuests", description="Number of guests (optional)"
    )  # Attribute
    country_of_guests: list[str] | None = Field(
        None, alias="countryOfGuests", description="Array of country codes of guests (optional)"
    )  # Attribute
    temporal: TemporalResponse = Field(
        ..., description="Temporal composite"
    )  # Composite

    @model_serializer(mode='wrap')
    def _serialize_model(self, serializer, info):
        """Exclude activityName from response when it's None."""
        data = serializer(self)
        if data.get('activityName') is None:
            data.pop('activityName', None)
        return data


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


class ActivityErrorDetail(BaseModel):
    """Error detail for a failed activity in processing."""

    model_config = ConfigDict(
        title="activity.ActivityErrorDetail",
        populate_by_name=True,
    )

    loc: list[str | int] = Field(
        default_factory=list,
        description="Location of the error (field path)",
        examples=[["activities", 0, "areaId"], ["activities", 1, "url"]],
    )
    msg: str = Field(
        ...,
        description="Error message describing what went wrong",
        examples=[
            "Competent authority with competent_authority_id 'invalid' not found",
            "Activity with platformActivityId 'abc-123' already exists",
        ],
    )
    type: str = Field(
        ...,
        description="Error type classification",
        examples=["business_logic_error", "duplicate_resource", "integrity_error"],
    )


class FailedActivity(BaseModel):
    """Represents a failed activity with its original request data and errors."""

    model_config = ConfigDict(
        title="activity.FailedActivity",
        populate_by_name=True,
    )

    activityIndex: int = Field(
        ...,
        alias="activityIndex",
        description="Index of the activity in the original request (0-based)",
        examples=[0, 1, 2],
    )
    activity: ActivityRequest = Field(
        ...,
        description="Original activity request data that failed",
    )
    errors: list[ActivityErrorDetail] = Field(
        ...,
        description="List of errors that occurred for this activity",
    )


class SuccessfulActivity(BaseModel):
    """Represents a successfully processed activity with its original request data (including generated ID)."""

    model_config = ConfigDict(
        title="activity.SuccessfulActivity",
        populate_by_name=True,
    )

    activityIndex: int = Field(
        ...,
        alias="activityIndex",
        description="Index of the activity in the original request (0-based)",
        examples=[0, 1, 2],
    )
    activity: ActivityRequest = Field(
        ...,
        description="Original activity request data that succeeded (includes generated activityId)",
    )


class ActivityProcessingResponse(BaseModel):
    """Response for activity processing with partial success/failure support."""

    model_config = ConfigDict(
        title="activity.ActivityProcessingResponse",
        populate_by_name=True,
    )

    message: str = Field(
        ...,
        description="Summary message of the processing result",
        examples=[
            "Processed 10 activities: 8 succeeded, 2 failed",
            "Processed 5 activities: 5 succeeded, 0 failed",
            "Processed 3 activities: 0 succeeded, 3 failed",
        ],
    )
    totalProcessed: int = Field(
        ...,
        alias="totalProcessed",
        description="Total number of activities submitted",
        examples=[10, 5, 3],
    )
    succeeded: int = Field(
        ...,
        description="Number of activities that succeeded",
        examples=[8, 5, 0],
    )
    failed: int = Field(
        ...,
        description="Number of activities that failed",
        examples=[2, 0, 3],
    )
    successes: list[SuccessfulActivity] = Field(
        default_factory=list,
        description="List of activities that succeeded (empty if all failed)",
    )
    failures: list[FailedActivity] = Field(
        default_factory=list,
        description="List of activities that failed (empty if all succeeded)",
    )
