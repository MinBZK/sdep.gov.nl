"""Initial schema.

Revision ID: 001
Revises:
Create Date: 2025-11-12

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


def generate_area_id() -> str:
    """Generate a random lowercase alphanumeric area_id."""
    return uuid.uuid4().hex[:20]

# Revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create competent_authority table
    op.create_table(
        "competent_authority",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("competent_authority_id", sa.String(length=64), nullable=False),
        sa.Column("competent_authority_name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_competent_authority")),
        sa.UniqueConstraint("competent_authority_id", name=op.f("uq_competent_authority_competent_authority_id")),
    )
    op.create_index(op.f("ix_competent_authority_id"), "competent_authority", ["id"], unique=False)
    op.create_index(op.f("ix_competent_authority_competent_authority_id"), "competent_authority", ["competent_authority_id"], unique=True)

    # Create area table
    op.create_table(
        "area",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("area_id", sa.String(length=64), nullable=False, server_default=sa.text("gen_random_uuid()::text")),
        sa.Column("filename", sa.String(length=64), nullable=False),
        sa.Column("filedata", sa.LargeBinary(), nullable=False),
        sa.Column("competent_authority_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["competent_authority_id"], ["competent_authority.id"], name=op.f("fk_area_competent_authority_id_competent_authority")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_area")),
        sa.UniqueConstraint("area_id", name=op.f("uq_area_area_id")),
    )
    op.create_index(op.f("ix_area_id"), "area", ["id"], unique=False)
    op.create_index(op.f("ix_area_area_id"), "area", ["area_id"], unique=True)
    op.create_index(op.f("ix_area_competent_authority_id"), "area", ["competent_authority_id"], unique=False)

    # Create platform table
    op.create_table(
        "platform",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform_id", sa.String(length=32), nullable=False),
        sa.Column("platform_name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform")),
        sa.UniqueConstraint("platform_id", name=op.f("uq_platform_platform_id")),
    )
    op.create_index(op.f("ix_platform_id"), "platform", ["id"], unique=False)
    op.create_index(op.f("ix_platform_platform_id"), "platform", ["platform_id"], unique=True)

    # Create activity_data table
    op.create_table(
        "activity_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=128), nullable=False),
        sa.Column("address_street", sa.String(length=64), nullable=False),
        sa.Column("address_number", sa.Integer(), nullable=False),
        sa.Column("address_letter", sa.String(length=1), nullable=True),
        sa.Column("address_addition", sa.String(length=10), nullable=True),
        sa.Column("address_postal_code", sa.String(length=8), nullable=False),
        sa.Column("address_city", sa.String(length=64), nullable=False),
        sa.Column("registration_number", sa.String(length=32), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=False),
        sa.Column("number_of_guests", sa.Integer(), nullable=False),
        sa.Column(
            "country_of_guests",
            postgresql.ARRAY(sa.String(length=32)),
            nullable=False,
        ),
        sa.Column("temporal_start_date_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temporal_end_date_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], name=op.f("fk_activity_data_area_id_area")),
        sa.ForeignKeyConstraint(["platform_id"], ["platform.id"], name=op.f("fk_activity_data_platform_id_platform")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_data")),
        sa.UniqueConstraint(
            "url",
            "temporal_start_date_time",
            "temporal_end_date_time",
            name="uq_activity_data_url_temporal",
        ),
    )
    op.create_index(
        op.f("ix_activity_data_id"), "activity_data", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_activity_data_area_id"), "activity_data", ["area_id"], unique=False
    )
    op.create_index(
        op.f("ix_activity_data_platform_id"), "activity_data", ["platform_id"], unique=False
    )

    # Add check constraint for number_of_guests range (1-1024)
    op.create_check_constraint(
        "ck_activity_data_number_of_guests_range",
        "activity_data",
        "number_of_guests >= 1 AND number_of_guests <= 1024"
    )

    # Add check constraint for country_of_guests array length (1-1024)
    op.create_check_constraint(
        "ck_activity_data_country_of_guests_length",
        "activity_data",
        "array_length(country_of_guests, 1) >= 1 AND array_length(country_of_guests, 1) <= 1024"
    )

    # Add check constraint for temporal_start_date_time year >= 2025
    op.create_check_constraint(
        "ck_activity_data_temporal_start_year",
        "activity_data",
        "EXTRACT(YEAR FROM temporal_start_date_time) >= 2025"
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop activity_data table constraints
    op.drop_constraint("ck_activity_data_temporal_start_year", "activity_data", type_="check")
    op.drop_constraint("ck_activity_data_country_of_guests_length", "activity_data", type_="check")
    op.drop_constraint("ck_activity_data_number_of_guests_range", "activity_data", type_="check")
    op.drop_index(op.f("ix_activity_data_platform_id"), table_name="activity_data")
    op.drop_index(op.f("ix_activity_data_area_id"), table_name="activity_data")
    op.drop_index(op.f("ix_activity_data_id"), table_name="activity_data")
    op.drop_table("activity_data")

    # Drop platform table
    op.drop_index(op.f("ix_platform_platform_id"), table_name="platform")
    op.drop_index(op.f("ix_platform_id"), table_name="platform")
    op.drop_table("platform")

    # Drop area table
    op.drop_index(op.f("ix_area_competent_authority_id"), table_name="area")
    op.drop_index(op.f("ix_area_area_id"), table_name="area")
    op.drop_index(op.f("ix_area_id"), table_name="area")
    op.drop_table("area")

    # Drop competent_authority table
    op.drop_index(op.f("ix_competent_authority_competent_authority_id"), table_name="competent_authority")
    op.drop_index(op.f("ix_competent_authority_id"), table_name="competent_authority")
    op.drop_table("competent_authority")
