"""Area model."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base


def generate_area_id() -> str:
    """Generate a random lowercase alphanumeric area_id."""
    return uuid.uuid4().hex[:20]  # Generate 20 character lowercase alphanumeric string (UUID hex)


class Area(Base):
    """Area model representing geographical areas subject to STR regulation.

    An area constitutes a unit of short-term rental regulation (STR).
    An area is supplied by (regulated by) a competent authority (CA).
    An area is expressed as a binary (shapefile).
    """

    __tablename__ = "area"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Attributes
    area_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=generate_area_id, index=True
    )  # Lowercase alphanumeric with dashes, auto-generated if not supplied, for example "amsterdam-area-0363"

    filename: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # Mandatory, for example "Amsterdam.zip"

    filedata: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )  # Mandatory, for example: a .zip with a collection of ESRI shapefile files

    competent_authority_id: Mapped[int] = mapped_column(
        ForeignKey("competent_authority.id"), nullable=False, index=True
    )  # Reference - foreign key to CompetentAuthority

    # Audit attributes
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), nullable=False
    )  # Always present

    # References
    competent_authority: Mapped["CompetentAuthority"] = relationship(
        "CompetentAuthority", back_populates="areas"
    )  # One to one (mandatory)

    activity_data: Mapped[list["ActivityData"]] = relationship(
        "ActivityData", back_populates="area"
    )  # Zero to many

    def __repr__(self) -> str:
        """String representation of Area."""
        return f"<Area(id={self.id}, area_id='{self.area_id}', filename='{self.filename}')>"
