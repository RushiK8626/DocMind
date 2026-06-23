"""Module conversations.py."""
from sqlalchemy.orm import instrumentation
from sqlalchemy.orm import instrumentation
import logging

from sqlalchemy import select
from sqlalchemy import func
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models.chat_conversation import ChatConversation

logger = logging.getLogger('app')

conversations_bp = Blueprint("conversations", __name__)


@conversations_bp.route("/", methods=["GET"])
@jwt_required()
def get_project_conversations():
    """get_project_conversations function."""
    current_user_id = get_jwt_identity()
    project_id = request.args.get("project_id")

    if not project_id:
        return (
            jsonify({"status": "error", "message": "Field 'project_id' is required."}),
            400,
        )

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = max(1, min(per_page, 50))

    pagination = (
        ChatConversation.query.filter_by(user_id=current_user_id, project_id=project_id)
        .order_by(ChatConversation.updated_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return (
        jsonify(
            {
                "status": "success",
                "conversations": [
                    {
                        "id": c.id,
                        "title": c.title,
                        "created_at": c.created_at.isoformat(),
                        "updated_at": c.updated_at.isoformat(),
                    }
                    for c in pagination.items
                ],
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total_pages": pagination.pages,
                    "total_items": pagination.total,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
            }
        ),
        200,
    )


@conversations_bp.route("/<string:conversation_id>", methods=["GET"])
@jwt_required()
def get_conversation(conversation_id):
    """get_conversation function."""
    current_user_id = get_jwt_identity()

    stmt = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user_id,
    )
    conversation = db.session.execute(stmt).scalar_one_or_none()

    if not conversation:
        return jsonify({"status": "error", "message": "Conversation not found."}), 404

    return (
        jsonify(
            {
                "status": "success",
                "conversation": {
                    "id": conversation.id,
                    "title": conversation.title,
                    "created_at": conversation.created_at.isoformat(),
                    "updated_at": conversation.updated_at.isoformat(),
                    "messages": [
                        {
                            "id": m.id,
                            "role": m.role.value,
                            "content": m.content,
                            "created_at": m.created_at.isoformat(),
                        }
                        for m in conversation.messages
                    ],
                },
            }
        ),
        200,
    )


@conversations_bp.route("/conversations/<string:conversation_id>", methods=["PATCH"])
@jwt_required()
def update_project(conversation_id):
    """update_project function."""
    current_user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    conversation = ChatConversation.query.filter_by(
        id=conversation_id, user_id=current_user_id
    ).first()
    if not conversation:
        return jsonify({"status": "error", "message": "Conversation not found."}), 404

    allowed_fields = {"title"}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"No valid fields to update. Allowed: {sorted(allowed_fields)}",
                }
            ),
            400,
        )

    if "title" in updates:
        new_title = (updates["title"] or "").strip()
        if not new_title:
            return (
                jsonify({"status": "error", "message": "'title' cannot be empty."}),
                400,
            )

        duplicate = ChatConversation.query.filter(
            ChatConversation.user_id == current_user_id,
            ChatConversation.title == new_title,
            ChatConversation.id != conversation_id,
        ).first()
        if duplicate:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"A project named '{new_title}' already exists.",
                    }
                ),
                409,
            )

        conversation.title = new_title

    try:
        conversation.updated_at = func.now()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Failed to update conversation: '{conversation_id}'")
        return jsonify({"status": "error", "message": str(e)}), 500

    return (
        jsonify(
            {
                "status": "success",
                "message": "Conversation updated",
                "conversation_id": conversation_id,
                "title": new_title,
            }
        ),
        200,
    )


@conversations_bp.route("/<string:conversation_id>", methods=["DELETE"])
@jwt_required()
def delete_conversation(conversation_id):
    """delete_conversation function."""
    current_user_id = get_jwt_identity()

    stmt = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user_id,
    )
    conversation = db.session.execute(stmt).scalar_one_or_none()

    if not conversation:
        return jsonify({"status": "error", "message": "Conversation not found."}), 404

    try:
        db.session.delete(conversation)
        db.session.commit()
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Conversation deleted.",
                    "conversation_id": conversation_id,
                }
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Failed to delete conversation: '{conversation_id}'")
        return jsonify({"status": "error", "message": str(e)}), 500
