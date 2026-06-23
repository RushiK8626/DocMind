"""Module chats.py."""

from sqlalchemy.orm import query
import logging

from flask import current_app
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from app.extensions import db
from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage, MessageRole
from app.agents.graph import build_graph

logger = logging.getLogger(__name__)

chats_bp = Blueprint("chats", __name__)


def _chunks_to_context(chunks: list[dict]) -> str:
    """_chunks_to_context function."""
    if not chunks:
        return "No relevant context retrieved from knowledge base."

    parts = []

    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        src = meta.get("source", meta.get("filename", chunk["id"]))
        parts.append(f"[Chunk {i}] Source: {src}\n{chunk['document']}")

    return "\n\n---\n\n".join(parts)


@chats_bp.route("/answer", methods=["POST"])
@jwt_required()
def answer():
    """answer function."""
    current_user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()

    conversation_id = data.get("conversation_id")
    project_id = data.get("project_id")

    top_k = int(data.get("top_k", current_app.config["TOP_K_RESULTS"]))

    if not query:
        return jsonify(
            {"status": "error", "message": "Field 'query' is required."}
        ), 400

    is_new_conversation = False
    conversation = None

    if conversation_id:
        conversation = ChatConversation.query.filter_by(
            id=conversation_id,
            user_id=current_user_id,
        ).first()

        if not conversation:
            return jsonify(
                {"status": "error", "message": "Conversation not found."}
            ), 404
    else:
        is_new_conversation = True

    top_k = max(1, min(top_k, 10))

    try:
        graph = build_graph(
            current_app.config,
            current_user_id,
            project_id,
        )

        final_state = graph.invoke(
            {
                "query": query,
                "user_id": current_user_id,
                "project_id": project_id,
                "top_k": top_k,
                "messages": [],
            }
        )

        answer_text = final_state["final_answer"]
        reasoning_text = final_state.get("reasoning_output", "")
        raw_chunks = final_state.get("raw_chunks", [])

        if is_new_conversation:
            title = query[:30] + ("…" if len(query) > 30 else "")

            conversation = ChatConversation(
                user_id=current_user_id,
                project_id=project_id,
                title=title,
            )

            db.session.add(conversation)
            db.session.flush()

            conversation_id = conversation.id

        user_message = ChatMessage(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=query,
        )

        db.session.add(user_message)
        db.session.flush()

        assistant_message = ChatMessage(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=answer_text,
        )

        db.session.add(assistant_message)
        db.session.flush()

        if not is_new_conversation:
            conversation.updated_at = func.now()

        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "query": query,
                "answer": answer_text,
                "conversation_id": conversation.id,
                "is_new_conversation": is_new_conversation,
                "pipeline": {
                    "reasoning_output": reasoning_text,
                },
                "raw_chunks": raw_chunks,
                "user_message_id": user_message.id,
                "assistant_message_id": assistant_message.id,
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(f"Pipeline failed for query: '{query}'")

        return jsonify(
            {
                "status": "error",
                "message": str(e),
            }
        ), 500