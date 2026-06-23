"""Module page.py."""
import uuid

from sqlalchemy import (
    String,
    Integer,
    Text,
    Numeric,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Page(db.Model):
    """Page class."""

    __tablename__ = "page"

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_page_number"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )

    page_number: Mapped[int] = mapped_column(Integer, nullable=False)

    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    width: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    height: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document = relationship("Document", back_populates="pages")

    layout_elements = relationship(
        "LayoutElement", back_populates="page", cascade="all, delete-orphan"
    )
