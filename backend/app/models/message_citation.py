import uuid
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db


class MessageCitation(db.Model):
    __tablename__ = "message_citation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    message_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_message.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    layout_element_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("layout_element.id", ondelete="CASCADE"),
        nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # [SOURCE N]

    message        = relationship("ChatMessage",     back_populates="citations")
    layout_element = relationship("LayoutElement")