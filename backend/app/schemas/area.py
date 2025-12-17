"""Pydantic schemas for Area API requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer


class AreaRequest(BaseModel):
    """Area request schema for creating areas (shapefiles).

    Competent Authority:
    - NOT in request payload (extracted from JWT token at API layer)
    - CompetentAuthorityId comes from token's client_id claim
    - CompetentAuthorityName comes from token's client_name claim
    - Will be auto-created if it doesn't exist yet

    Area ID:
    - Optional: If not provided, will be auto-generated (RFC 9562 UUID)

    Area Name:
    - Optional: Human-readable name (max 128 chars)

    Validation Layer:
    - Validates all syntax constraints (lengths, types)
    - Accepts base64-encoded binary filedata in JSON requests

    File Data Encoding:
    - The 'filedata' field MUST be base64-encoded when sending JSON requests
    - Pydantic automatically decodes base64 strings to bytes
    - Example (bash): base64 -w 0 yourfile.zip
    - Example (Python): base64.b64encode(file_bytes).decode('utf-8')

    Constraints (enforced at database level):
    - Unique constraint: (areaId, createdAt) for versioning support
    """

    model_config = ConfigDict(
        title="area.AreaRequest",
        populate_by_name=True,
    )

    area_id: str | None = Field(
        None,
        alias="areaId",
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9-]+$",
        description="Area functional ID (optional, auto-generated UUID if not provided; lowercase alphanumeric with hyphens, max 64 chars)",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )  # Functional ID

    area_name: str | None = Field(
        None,
        alias="areaName",
        max_length=64,
        description="Area name (optional, human-readable, max 64 chars)",
        examples=["Amsterdam Central"],
    )  # Functional name

    filename: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Filename of the area shapefile (e.g., .zip with ESRI shapefile files)",
        examples=["Amsterdam.zip"],
    )  # Attribute

    filedata: bytes = Field(
        ...,
        description="Base64-encoded binary file data. When sending JSON requests, encode your file as base64. Example: base64.b64encode(file_bytes).decode('utf-8'). The API will automatically decode the base64 string to bytes.",
        examples=["UEsDBBQAAAAIAG1heFkAAAAA..."],  # Truncated base64 example
    )  # Attribute

    @field_validator("filedata")
    @classmethod
    def validate_filedata_size(cls, v: bytes) -> bytes:
        """Validate that filedata is at most 1 MiB (1048576 bytes).

        This limit ensures predictable performance and reduces abuse risk.
        """
        max_size = 1048576  # 1 MiB
        if len(v) > max_size:
            raise ValueError(
                f"filedata exceeds maximum size of 1 MiB ({max_size} bytes). "
                f"Received {len(v)} bytes."
            )
        return v

    def to_service_dict(
        self, competent_authority_id: str, competent_authority_name: str
    ) -> dict:
        """
        Convert Pydantic model to dictionary for service layer.

        Normalizes competent authority info from JWT token to each area.
        Converts all field names to snake_case.

        Args:
            competent_authority_id: Competent authority ID from JWT token (client_id claim)
            competent_authority_name: Competent authority name from JWT token (client_name claim)

        Returns:
            Dictionary with snake_case keys
        """
        return {
            "competent_authority_id_str": competent_authority_id,
            "competent_authority_name": competent_authority_name,
            "area_id": self.area_id,
            "area_name": self.area_name,
            "filename": self.filename,
            "filedata": self.filedata,
        }


class AreaListRequest(BaseModel):
    """List of areas for bulk submission.

    Validation Layer:
    - Validates the entire list
    - Each area is validated individually
    - Competent authorities are auto-created if not present

    File Data Format:
    - All filedata fields in the areas array must be base64-encoded
    - See AreaRequest for encoding examples
    """

    model_config = ConfigDict(title="area.AreaListRequest")

    areas: list[AreaRequest] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of areas to process (max 1000 per batch)",
    )

    def to_service_list(
        self, competent_authority_id: str, competent_authority_name: str
    ) -> list[dict]:
        """
        Convert list of Pydantic models to list of dictionaries for service layer.

        Normalizes competent authority info (from JWT token) from batch level to each area.
        This happens at the API layer to keep service layer focused on business logic.

        Args:
            competent_authority_id: Competent authority ID from JWT token (client_id claim)
            competent_authority_name: Competent authority name from JWT token (client_name claim)

        Returns:
            List of dictionaries with snake_case keys, each containing normalized competent authority info
        """
        return [
            area.to_service_dict(
                competent_authority_id=competent_authority_id,
                competent_authority_name=competent_authority_name,
            )
            for area in self.areas
        ]


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
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9-]+$",
        description="Area functional ID (lowercase alphanumeric with hyphens, max 64 chars)",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )  # Functional ID
    area_name: str | None = Field(
        None,
        alias="areaName",
        max_length=64,
        description="Area name (optional, max 64 chars)",
        examples=["Amsterdam Central"],
    )  # Functional name
    created_at: datetime = Field(
        ...,
        alias="createdAt",
        description="Timestamp when the area was created",
        examples=["2025-01-15T10:30:00Z"],
    )  # Attribute
    competent_authority_id: str = Field(
        ...,
        alias="competentAuthorityId",
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9-]+$",
        description="Competent authority functional ID who submitted the area (lowercase alphanumeric with hyphens, max 64 chars)",
        examples=["sdep-ca-0363"],
    )  # Attribute
    competent_authority_name: str | None = Field(
        None,
        alias="competentAuthorityName",
        max_length=64,
        description="Competent authority name (optional, max 64 chars)",
        examples=["Gemeente Amsterdam"],
    )  # Attribute
    filename: str = Field(
        ...,
        max_length=64,
        description="Area filename",
        examples=["Amsterdam.zip"],
    )  # Attribute

    @model_serializer(mode='wrap')
    def _serialize_model(self, serializer, info):
        """Exclude areaName from response when it's None."""
        data = serializer(self)
        if data.get('areaName') is None:
            data.pop('areaName', None)
        return data


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


class AreaErrorDetail(BaseModel):
    """Error detail for a failed area in processing."""

    model_config = ConfigDict(
        title="area.AreaErrorDetail",
        populate_by_name=True,
    )

    loc: list[str | int] = Field(
        default_factory=list,
        description="Location of the error (field path)",
        examples=[["areas", 0, "filename"], ["areas", 1, "filedata"]],
    )
    msg: str = Field(
        ...,
        description="Error message describing what went wrong",
        examples=[
            "Competent authority with competent_authority_id 'invalid' not found",
            "Area with areaId 'abc-123' already exists",
        ],
    )
    type: str = Field(
        ...,
        description="Error type classification",
        examples=["business_logic_error", "duplicate_resource", "integrity_error"],
    )


class FailedArea(BaseModel):
    """Represents a failed area with its original request data and errors."""

    model_config = ConfigDict(
        title="area.FailedArea",
        populate_by_name=True,
    )

    areaIndex: int = Field(
        ...,
        alias="areaIndex",
        description="Index of the area in the original request (0-based)",
        examples=[0, 1, 2],
    )
    area: AreaRequest = Field(
        ...,
        description="Original area request data that failed",
    )
    errors: list[AreaErrorDetail] = Field(
        ...,
        description="List of errors that occurred for this area",
    )


class SuccessfulArea(BaseModel):
    """Represents a successfully processed area with its original request data (including generated ID)."""

    model_config = ConfigDict(
        title="area.SuccessfulArea",
        populate_by_name=True,
    )

    areaIndex: int = Field(
        ...,
        alias="areaIndex",
        description="Index of the area in the original request (0-based)",
        examples=[0, 1, 2],
    )
    area: AreaRequest = Field(
        ...,
        description="Original area request data that succeeded (includes generated areaId)",
    )


class AreaProcessingResponse(BaseModel):
    """Response for area processing with partial success/failure support."""

    model_config = ConfigDict(
        title="area.AreaProcessingResponse",
        populate_by_name=True,
    )

    message: str = Field(
        ...,
        description="Summary message of the processing result",
        examples=[
            "Processed 10 areas: 8 succeeded, 2 failed",
            "Processed 5 areas: 5 succeeded, 0 failed",
            "Processed 3 areas: 0 succeeded, 3 failed",
        ],
    )
    totalProcessed: int = Field(
        ...,
        alias="totalProcessed",
        description="Total number of areas submitted",
        examples=[10, 5, 3],
    )
    succeeded: int = Field(
        ...,
        description="Number of areas that succeeded",
        examples=[8, 5, 0],
    )
    failed: int = Field(
        ...,
        description="Number of areas that failed",
        examples=[2, 0, 3],
    )
    successes: list[SuccessfulArea] = Field(
        default_factory=list,
        description="List of areas that succeeded (empty if all failed)",
    )
    failures: list[FailedArea] = Field(
        default_factory=list,
        description="List of areas that failed (empty if all succeeded)",
    )
