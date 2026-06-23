"""Module project.py."""
import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Project(db.Model):
    """Project class."""

    __tablename__ = "project"

    __table_args__ = (
        Index("ix_project_user_id_created_at", "user_id", "created_at"),
        UniqueConstraint("user_id", "project_name", name="uq_project_user_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_name: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="projects")

    conversations = relationship(
        "ChatConversation",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    documents = relationship(
        "Document",
        back_populates="project",
        cascade="all, delete-orphan",
    )
