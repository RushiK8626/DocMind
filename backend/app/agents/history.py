"""Module history.py. Handles loading chat history for the graph."""
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.models.chat_message import ChatMessage, MessageRole


def load_conversation_history(conversation_id: str | None, limit: int = 20) -> list:
    """
    Load recent messages from DB and convert to LangChain message objects.
    Returns empty list if no conversation yet (first message).
    """
    if not conversation_id:
        return []

    messages = (
        ChatMessage.query
        .filter_by(conversation_id=conversation_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)       # cap history to avoid context overflow
        .all()
    )

    history = []
    for msg in messages:
        if msg.role == MessageRole.USER:
            history.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            history.append(AIMessage(content=msg.content))

    return history