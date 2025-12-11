"""Activity model."""

import json
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, composite, mapped_column, relationship

from app.db.config import Base
from app.models.address import Address
from app.models.temporal import Temporal


def generate_activity_id() -> str:
    """Generate a random lowercase alphanumeric activity_id."""
    return uuid.uuid4().hex[:20]


class StringArray(TypeDecorator):
    """Custom type for storing arrays as JSON in SQLite and ARRAY in PostgreSQL."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Load the appropriate type based on dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String(32)))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        """Convert list to JSON string for SQLite."""
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        """Convert JSON string back to list for SQLite."""
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.loads(value)


class Activity(Base):
    """Activity model representing an actual rental activity.

    An Activity represents an actual rental activity.
    - The activity can apply to the address as a whole
    - The activity can also apply to part of the address (a unit)

    The host has obtained a registration number for the address (conform legislation).
    On the platform, the host has replicated the registration number in each advertisement,
    in case the address is advertised in parts.
    The registration number is consequently replicated in each Activity.

    An Activity has a unique constraint:
    - The combination of activity_id, platform_id, url, temporal start datetime, and temporal end datetime must be unique
    Although registrationNumber is a string, it still is commonly referred to as "number".
    """

    __tablename__ = "activity"
    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "platform_id",
            "url",
            "temporal_start_date_time",
            "temporal_end_date_time",
            name="uq_activity_all",
        ),
        CheckConstraint(
            "number_of_guests >= 1 AND number_of_guests <= 1024",
            name="ck_activity_number_of_guests_range",
        ),
        # PostgreSQL-specific constraint for array length (array_length function not available in SQLite)
        CheckConstraint(
            "array_length(country_of_guests, 1) >= 1 AND array_length(country_of_guests, 1) <= 1024",
            name="ck_activity_country_of_guests_length",
        ).ddl_if(dialect="postgresql"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Attributes
    activity_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default=generate_activity_id, index=True
    )  # Lowercase alphanumeric, auto-generated if not supplied, for example "sdep-str01-001"

    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platform.id"), nullable=False, index=True
    )  # Reference - foreign key to Platform

    area_id: Mapped[int] = mapped_column(
        ForeignKey("area.id"), nullable=False, index=True
    )  # Reference - foreign key to Area

    url: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # Mandatory, for example "http://example.com/my-advertisement"

    # Composite attributes - Address
    address_street: Mapped[str] = mapped_column(String(64), nullable=False)
    address_number: Mapped[int] = mapped_column(Integer, nullable=False)
    address_letter: Mapped[str | None] = mapped_column(String(1), nullable=True)
    address_addition: Mapped[str | None] = mapped_column(String(10), nullable=True)
    address_postal_code: Mapped[str] = mapped_column(String(8), nullable=False)
    address_city: Mapped[str] = mapped_column(String(64), nullable=False)

    registration_number: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # Mandatory, for example "REG123456"

    number_of_guests: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Mandatory, min 1, max 1024

    country_of_guests: Mapped[list[str]] = mapped_column(
        StringArray, nullable=False
    )  # Mandatory, min 1, max 1024

    # Composite attributes - Temporal
    temporal_start_date_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    temporal_end_date_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Audit attributes
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), nullable=False
    )  # Always present

    # Composites
    address: Mapped[Address] = composite(
        Address,
        address_street,
        address_number,
        address_letter,
        address_addition,
        address_postal_code,
        address_city,
    )
    temporal: Mapped[Temporal] = composite(
        Temporal, temporal_start_date_time, temporal_end_date_time
    )

    # References
    area: Mapped["Area"] = relationship(
        "Area", back_populates="activities"
    )  # Zero to many to one (mandatory)

    platform: Mapped["Platform"] = relationship(
        "Platform", back_populates="activities"
    )  # Zero to many to one (mandatory)

    def __repr__(self) -> str:
        """String representation of Activity."""
        return f"<Activity(id={self.id}, activity_id='{self.activity_id}', url='{self.url}', registration_number='{self.registration_number}')>"
