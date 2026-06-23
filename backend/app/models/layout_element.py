"""Module layout_element.py."""
import uuid

from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

from enum import Enum
from sqlalchemy import Enum as SQLEnum


class ElementType(Enum):
    """ElementType class."""

    TEXT = "text"
    INPUT_FIELD = "input_field"
    CHECKBOX = "checkbox"
    TABLE_CELL = "table_cell"


class LayoutElement(db.Model):
    """LayoutElement class."""

    __tablename__ = "layout_element"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    page_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("page.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    element_type: Mapped[ElementType] = mapped_column(
        SQLEnum(ElementType), nullable=False
    )

    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    box_top: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)

    box_left: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)

    box_width: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)

    box_height: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)

    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    page = relationship("Page", back_populates="layout_elements")
