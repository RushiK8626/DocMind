"""Module document.py."""
import uuid

from sqlalchemy import String, Integer, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Document(db.Model):
    """Document class."""

    __tablename__ = "document"

    __table_args__ = (
        db.Index("idx_document_user_created", "user_id", "created_at"),
        db.Index("idx_document_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    file_url: Mapped[str] = mapped_column(Text, nullable=False)

    thumbnail_key: Mapped[str] = mapped_column(Text)

    file_type: Mapped[str] = mapped_column(String(50), nullable=False)

    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")

    extracted_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="documents")

    project = relationship("Project", back_populates="documents")

    pages = relationship(
        "Page", back_populates="document", cascade="all, delete-orphan"
    )
