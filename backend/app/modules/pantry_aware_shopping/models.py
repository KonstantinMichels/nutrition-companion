from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now

if TYPE_CHECKING:
    from app.modules.shopping_lists.models import ShoppingList


class PantryAwareShoppingOperation(Base):
    __tablename__ = "pantry_aware_shopping_operations"
    __table_args__ = (
        UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_pantry_aware_operation"
        ),
        Index("ix_pantry_aware_target_created", "target_shopping_list_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_shopping_list_id: Mapped[UUID] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_scope_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_reference: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    pantry_date_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    other_open_lists_considered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    result_summary: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    target_shopping_list: Mapped[ShoppingList] = relationship()
