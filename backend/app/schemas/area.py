"""Pydantic schemas for Area API requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MetaDataRequest(BaseModel):
    """Metadata schema for area batch submissions.

    Contains metadata that applies to all areas in a batch submission.

    Note: This is kept as a placeholder for future batch-level metadata.
    Currently, no batch-level fields are required.
    """

    model_config = ConfigDict(
        title="area.MetaDataRequest",
        populate_by_name=True,
    )


class AreaRequest(BaseModel):
    """Area request schema for creating geographical areas.

    Validation Layer:
    - Validates all syntax constraints (lengths, types)
    - Converts camelCase (API) to snake_case (internal Python)
    - Accepts base64-encoded binary filedata in JSON requests

    File Data Encoding:
    - The 'filedata' field MUST be base64-encoded when sending JSON requests
    - Pydantic automatically decodes base64 strings to bytes
    - Example (bash): base64 -w 0 yourfile.zip
    - Example (Python): base64.b64encode(file_bytes).decode('utf-8')

    Area ID:
    - Optional: If not provided, will be auto-generated (UUID-based)
    - If provided: Must be lowercase alphanumeric with dashes (max 64 chars)

    Competent Authority:
    - NOT in request payload (extracted from JWT token at API layer)
    - CompetentAuthorityId comes from token's client_id claim
    - CompetentAuthorityName comes from token's client_name claim
    - Will be auto-created if it doesn't exist yet (similar to Platform in activities)
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
        description="Area identifier (optional, auto-generated if not provided). Lowercase alphanumeric with dashes.",
        examples=["amsterdam-area-0363"],
    )  # Attribute

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
            "area_id": self.area_id,
            "filename": self.filename,
            "filedata": self.filedata,
            "competent_authority_id_str": competent_authority_id,
            "competent_authority_name": competent_authority_name,
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

    metadata: MetaDataRequest = Field(
        ...,
        description="Metadata that applies to all areas in this batch (placeholder for future use)",
    )

    areas: list[AreaRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of areas to process (max 100 per batch)",
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
        max_length=64,
        description="Area unique identifier (enables retrieval of area)",
        examples=["amsterdam-area-0363"],
    )  # Attribute
    competent_authority_id: str = Field(
        ...,
        alias="competentAuthorityId",
        max_length=64,
        description="Competent authority id who submitted the area",
        examples=["sdep-ca-0363"],
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
