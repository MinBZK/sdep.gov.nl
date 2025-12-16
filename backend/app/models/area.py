"""Area model."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base


def generate_area_id() -> str:
    """Generate a random lowercase alphanumeric area_id."""
    return uuid.uuid4().hex[:20]  # Generate 20 character lowercase alphanumeric string (UUID hex)


class Area(Base):
    """Area model representing geographical areas (shapefiles) subject to STR regulation.

    An area constitutes a unit of short-term rental regulation (STR).
    An area is supplied by (regulated by) a competent authority (CA).
    An area is expressed as a binary (shapefile).

    Each area has a unique technical ID (20-character UUID) and an optional functional
    competent_authority_area_id that can be used for business identification.
    """

    __tablename__ = "area"
    __table_args__ = (
        CheckConstraint(
            "length(filedata) <= 1048576",
            name="ck_area_filedata_max_size",
        ),
    )

    # Primary key
    id: Mapped[str] = mapped_column(String(20), primary_key=True, index=True, default=generate_area_id)

    # Attributes

    competent_authority_id: Mapped[int] = mapped_column(
        ForeignKey("competent_authority.id"), nullable=False, index=True
    )  # Reference - foreign key to CompetentAuthority

    competent_authority_area_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )  # Lowercase alphanumeric with dashes, optional field, for example "amsterdam-area-0363"

    filename: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # Mandatory, for example "Amsterdam.zip"

    filedata: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )  # Mandatory, max size 1 MiB, for example: a .zip with a collection of ESRI shapefile files

    # Audit attributes
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )  # Always present, stored in UTC

    # References
    competent_authority: Mapped["CompetentAuthority"] = relationship(
        "CompetentAuthority", back_populates="areas"
    )  # One to one (mandatory)

    activities: Mapped[list["Activity"]] = relationship(
        "Activity", back_populates="area"
    )  # Zero to many

    def __repr__(self) -> str:
        """String representation of Area."""
        return f"<Area(id={self.id}, competent_authority_area_id='{self.competent_authority_area_id}', filename='{self.filename}')>"
