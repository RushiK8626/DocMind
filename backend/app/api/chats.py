"""API endpoints for chat conversations and message answering."""

from langchain_core.messages import SystemMessage
from PIL import ImageColor
from sqlalchemy.orm import query
import logging
import json

from flask import current_app
from flask import Blueprint, request, jsonify, current_app
from flask import Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from langchain_core.messages import SystemMessage, HumanMessage

from app.extensions import db
from app.agents.history import load_conversation_history
from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage, MessageRole
from app.models.message_citation import MessageCitation
from app.agents.graph import build_graph
from app.utils.citation_parser import extract_citations
from app.agents.nodes.reasoning_node import SYSTEM

logger = logging.getLogger(__name__)

chats_bp = Blueprint("chats", __name__)


def _chunks_to_context(chunks: list[dict]) -> str:
    """Format retrieval chunks into a combined context string."""
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
    """Execute the pipeline synchronously to generate an answer for the user's query."""
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
        
        history = load_conversation_history(conversation_id, limit=20)
        
        # Build initial messages: system + history + current query
        initial_messages = [
            SystemMessage(content=SYSTEM),   # import SYSTEM from reasoning_node.py
            *history,                        # previous turns
            HumanMessage(content=query),     # current user message
        ]


        final_state = graph.invoke(
            {
                "query": query,
                "user_id": current_user_id,
                "project_id": project_id,
                "top_k": top_k,
                "messages": initial_messages,
            }
        )

        answer_text = final_state["final_answer"]
        reasoning_traces = final_state.get("reasoning_trace", [])
        reasoning_text = "\n\n".join(reasoning_traces) if reasoning_traces else ""

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
            
        # After assistant_message is flushed
        citations = extract_citations(answer_text)  # parses [SOURCE N] blocks

        for c in citations:
            if not c.layout_element_id:
                continue

            db.session.add(MessageCitation(
                message_id=        assistant_message.id,
                layout_element_id= c.layout_element_id,
                page_number=       c.page_number or 0,
                chunk_index=       c.source_num,
            ))

        db.session.commit()

        return jsonify({
            "status":               "success",
            "query":                query,
            "answer":               answer_text,
            "conversation_id":      conversation.id,
            "is_new_conversation":  is_new_conversation,
            "user_message_id":      user_message.id,
            "assistant_message_id": assistant_message.id,
            "citations": [                              
                {
                    "source_num":        c.chunk_index,
                    "page_number":       c.page_number,
                    "layout_element_id": c.layout_element_id,
                }
                for c in assistant_message.citations   
            ],
            "pipeline": {
                "reasoning_output": reasoning_text,
            },
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(f"Pipeline failed for query: '{query}'")

        return jsonify(
            {
                "status": "error",
                "message": str(e),
            }
        ), 500


@chats_bp.route("/answer/stream", methods=["POST"])
@jwt_required()
def answer_stream():
    """Streaming version of /answer using SSE."""
    current_user_id = get_jwt_identity()
    data            = request.get_json(silent=True) or {}
    query           = (data.get("query") or "").strip()
    conversation_id = data.get("conversation_id")
    project_id      = data.get("project_id")
    top_k           = max(1, min(int(data.get("top_k", current_app.config["TOP_K_RESULTS"])), 10))

    if not query:
        return jsonify({"status": "error", "message": "Field 'query' is required."}), 400

    is_new_conversation = False
    conversation        = None

    if conversation_id:
        conversation = ChatConversation.query.filter_by(
            id=conversation_id, user_id=current_user_id
        ).first()
        if not conversation:
            return jsonify({"status": "error", "message": "Conversation not found."}), 404
    else:
        is_new_conversation = True

    def generate():
        nonlocal conversation, conversation_id, is_new_conversation
        
        full_answer = []

        try:
            graph = build_graph(current_app.config, current_user_id, project_id)

            final_state_values = None
            
            history = load_conversation_history(conversation_id, limit=20)
            
            # Build initial messages: system + history + current query
            initial_messages = [
                SystemMessage(content=SYSTEM),   # import SYSTEM from reasoning_node.py
                *history,                        # previous turns
                HumanMessage(content=query),     # current user message
            ]

            # Stream tokens from the answer node
            for mode, payload in graph.stream(
                {
                    "query":      query,
                    "user_id":    current_user_id,
                    "project_id": project_id,
                    "top_k":      top_k,
                    "messages":   initial_messages,
                },
                stream_mode=["messages", "values"],
            ):
                if mode == "messages":
                    message, metadata = payload
                    
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        for tc in message.tool_calls:
                            logger.info(f"Model invoked tool '{tc['name']}' with args: {tc['args']}")
                            
                    # Only stream tokens from the answer node, skip tool calls
                    if (
                        metadata.get("langgraph_node") == "answer"
                        and hasattr(message, "content")
                        and message.content
                    ):
                        token = message.content
                        full_answer.append(token)
                        payload = {
                            'type': 'token', 
                            'content': token
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                elif mode == "values":
                    final_state_values = payload

            # Pipeline done — persist to DB 
            answer_text = "".join(full_answer)

            if is_new_conversation:
                title        = query[:30] + ("…" if len(query) > 30 else "")
                conversation = ChatConversation(
                    user_id=current_user_id,
                    project_id=project_id,
                    title=title,
                )
                db.session.add(conversation)
                db.session.commit()
                conversation_id = conversation.id
                
                payload = {
                    'type':            'new_conversation',
                    'conversation_id': conversation_id,
                    'title':           conversation.title,
                }
                yield f"data: {json.dumps(payload)}\n\n"

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

            citations = extract_citations(answer_text)
            for c in citations:
                if not c.layout_element_id:
                    continue
                db.session.add(MessageCitation(
                    message_id=        assistant_message.id,
                    layout_element_id= c.layout_element_id,
                    page_number=       c.page_number or 0,
                    chunk_index=       c.source_num,
                ))

            db.session.commit()

            reasoning_traces = final_state_values.get("reasoning_trace", []) if final_state_values else []
            reasoning_text = "\n\n".join(reasoning_traces) if reasoning_traces else ""

            # Send final metadata event
            payload = {
                'type':                  'done',
                'conversation_id':       conversation_id,
                'is_new_conversation':   is_new_conversation,
                'user_message_id':       user_message.id,
                'assistant_message_id':  assistant_message.id,
                'citations': [                              
                    {
                        'source_num':        c.chunk_index,
                        'page_number':       c.page_number,
                        'layout_element_id': c.layout_element_id,
                    }
                    for c in assistant_message.citations   
                ],
                'pipeline': {
                    'reasoning_output': reasoning_text,
                },
            }
            yield f"data: {json.dumps(payload)}\n\n"

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Streaming pipeline failed for query: '{query}'")
            payload = {
                'type': 'error', 
                'message': str(e)
            }
            yield f"data: {json.dumps(payload)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":       "no-cache",
            "X-Accel-Buffering":   "no",     # disables Nginx buffering — critical
            "Connection":          "keep-alive",
        },
    )