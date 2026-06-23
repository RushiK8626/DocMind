"""Module user.py."""
import uuid

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    """User class."""

    __tablename__ = "user"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    documents = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )

    chat_conversations = relationship(
        "ChatConversation", back_populates="user", cascade="all, delete-orphan"
    )

    projects = relationship(
        "Project", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        """set_password function."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """check_password function."""
        return check_password_hash(self.password_hash, password)
