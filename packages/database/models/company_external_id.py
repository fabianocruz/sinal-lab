"""Company external IDs for cross-source deduplication."""

import uuid
from typing import Optional

from sqlalchemy import Float, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class CompanyExternalId(UUIDMixin, TimestampMixin, Base):
    """Cross-source dedup lookup. One company can have multiple external IDs."""

    __tablename__ = "company_external_ids"

    company_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    id_type: Mapped[str] = mapped_column(String(50), nullable=False)
    id_value: Mapped[str] = mapped_column(String(500), nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    __table_args__ = (
        UniqueConstraint("id_type", "id_value", name="uq_external_id_type_value"),
        Index("ix_company_ext_ids_slug", "company_slug"),
        Index("ix_company_ext_ids_type_value", "id_type", "id_value"),
    )

    def __repr__(self) -> str:
        return f"<CompanyExternalId(company_slug='{self.company_slug}', id_type='{self.id_type}', id_value='{self.id_value}')>"
