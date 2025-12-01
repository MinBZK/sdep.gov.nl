"""CompetentAuthority model."""

from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base


class CompetentAuthority(Base):
    """CompetentAuthority model representing regulatory authorities.

    A Competent Authority (CA) is a regulatory body responsible for short-term rental regulation.
    A Competent Authority can regulate multiple areas.
    """

    __tablename__ = "competent_authority"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Attributes
    competent_authority_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )  # Mandatory, unique, for example "0363"

    competent_authority_name: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # Mandatory, for example "Gemeente Amsterdam"

    # Audit attributes
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), nullable=False
    )  # Always present

    # References
    areas: Mapped[list["Area"]] = relationship(
        "Area", back_populates="competent_authority"
    )  # Zero to many

    def __repr__(self) -> str:
        """String representation of CompetentAuthority."""
        return f"<CompetentAuthority(id={self.id}, competent_authority_id='{self.competent_authority_id}', competent_authority_name='{self.competent_authority_name}')>"
