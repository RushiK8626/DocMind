"""Module chat_message.py."""
import uuid
from enum import Enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class MessageRole(Enum):
    """MessageRole class."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(db.Model):
    """ChatMessage class."""

    __tablename__ = "chat_message"

    __table_args__ = (
        db.Index("idx_message_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation = relationship("ChatConversation", back_populates="messages")

    citations = relationship("MessageCitation", back_populates="message", cascade="all, delete-orphan")