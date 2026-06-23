"""Module projects.py."""
from sqlalchemy.orm import instrumentation
from sqlalchemy.orm import instrumentation
from sqlalchemy import select
import logging

from sqlalchemy import func
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.chroma_service import get_chroma_service
from app.services.file_service import delete_s3_object
from app.models.project import Project
from app.extensions import db

logger = logging.getLogger('app')

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("", methods=["POST"])
@jwt_required()
def create_project():
    """create_project function."""
    current_user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    project_name = (data.get("project_name") or "").strip()
    description = (data.get("description") or "").strip() or None

    if not project_name:
        return (
            jsonify(
                {"status": "error", "message": "Field 'project_name' is required."}
            ),
            400,
        )

    existing = Project.query.filter_by(
        user_id=current_user_id, project_name=project_name
    ).first()

    existing = db.session.scalar(
        select(Project).where(
            Project.user_id == current_user_id, Project.project_name == project_name
        )
    )

    if existing:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"A project named '{project_name}' already exists.",
                }
            ),
            409,
        )

    try:
        project = Project(
            user_id=current_user_id,
            project_name=project_name,
            description=description,
        )
        db.session.add(project)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to create project")
        return jsonify({"status": "error", "message": str(e)}), 500

    return (
        jsonify(
            {
                "status": "success",
                "project": _serialize_project(project),
            }
        ),
        201,
    )


@projects_bp.route("/<string:project_id>", methods=["GET"])
@jwt_required()
def get_project(project_id):
    """get_project function."""
    current_user_id = get_jwt_identity()

    project = db.session.scalar(
        select(Project).where(
            Project.user_id == current_user_id, Project.id == project_id
        )
    )

    if not project:
        return jsonify({"status": "error", "message": "Project not found."}), 404

    return (
        jsonify(
            {
                "status": "success",
                "project": _serialize_project(project),
            }
        ),
        200,
    )


@projects_bp.route("", methods=["GET"])
@jwt_required()
def get_user_projects():
    """get_user_projects function."""
    current_user_id = get_jwt_identity()

    page = max(1, request.args.get("page", default=1, type=int))
    per_page = request.args.get("per_page", default=20, type=int)
    per_page = max(1, min(per_page, 100))

    pagination = (
        Project.query.filter(Project.user_id == current_user_id)
        .order_by(Project.updated_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return (
        jsonify(
            {
                "status": "success",
                "projects": [_serialize_project(p) for p in pagination.items],
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total_items": pagination.total,
                    "total_pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
            }
        ),
        200,
    )


@projects_bp.route("/<string:project_id>", methods=["PATCH"])
@jwt_required()
def update_project(project_id):
    """update_project function."""
    current_user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    project = Project.query.filter_by(id=project_id, user_id=current_user_id).first()
    if not project:
        return jsonify({"status": "error", "message": "Project not found."}), 404

    allowed_fields = {"project_name", "description"}
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

    if "project_name" in updates:
        new_name = (updates["project_name"] or "").strip()
        if not new_name:
            return (
                jsonify(
                    {"status": "error", "message": "'project_name' cannot be empty."}
                ),
                400,
            )

        duplicate = Project.query.filter(
            Project.user_id == current_user_id,
            Project.project_name == new_name,
            Project.id != project_id,
        ).first()
        if duplicate:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"A project named '{new_name}' already exists.",
                    }
                ),
                409,
            )

        project.project_name = new_name

    if "description" in updates:
        desc = updates["description"]
        project.description = (desc or "").strip() or None

    try:
        project.updated_at = func.now()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Failed to update project: '{project_id}'")
        return jsonify({"status": "error", "message": str(e)}), 500

    return (
        jsonify(
            {
                "status": "success",
                "project": _serialize_project(project),
            }
        ),
        200,
    )


@projects_bp.route("/<string:project_id>", methods=["DELETE"])
@jwt_required()
def delete_project(project_id):
    """delete_project function."""
    current_user_id = get_jwt_identity()

    project = Project.query.filter_by(id=project_id, user_id=current_user_id).first()
    if not project:
        return jsonify({"status": "error", "message": "Project not found."}), 404

    documents = list(project.documents)

    s3_failures = []
    for doc in documents:
        if not delete_s3_object(doc.file_url):
            s3_failures.append(doc.file_name)
            continue
        if doc.thumbnail_key and not delete_s3_object(doc.thumbnail_key):
            s3_failures.append(doc.file_name)

    if s3_failures:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to delete some files from S3. Project not deleted.",
                    "failed_files": s3_failures,
                }
            ),
            500,
        )

    try:
        get_chroma_service().delete(where={"project_id": project_id})
    except Exception as e:
        logger.exception(f"Failed to delete Chroma vectors for project: '{project_id}'")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to clean up vector store. Project not deleted.",
                }
            ),
            500,
        )

    try:
        db.session.delete(project)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Failed to delete project: '{project_id}'")
        return jsonify({"status": "error", "message": str(e)}), 500

    return (
        jsonify(
            {
                "status": "success",
                "message": "Project and all associated data deleted.",
                "project_id": project_id,
            }
        ),
        200,
    )


def _serialize_project(project):
    """_serialize_project function."""
    return {
        "id": project.id,
        "project_name": project.project_name,
        "description": project.description,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "document_count": len(project.documents),
    }
