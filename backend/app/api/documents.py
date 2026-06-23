"""Module documents.py."""
from sqlalchemy.orm import instrumentation
from sqlalchemy.orm import instrumentation
import tempfile
import os
import asyncio

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.document import Document
from app.models.project import Project
from app.tasks.ocr_tasks import run_ocr_pipeline_task
from app.services.file_service import (
    generate_thumbnail,
    get_user_document,
    upload_file_to_s3,
    delete_s3_object,
    generate_presigned_url,
)

documents_bp = Blueprint("documents", __name__)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "docx"}
UPLOAD_FOLDER = "/tmp/multimodal_uploads"


def allowed_file(filename: str) -> bool:
    """allowed_file function."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_single(doc: Document, tmp_path: str) -> dict:
    """Queue document for background processing via Celery."""
    try:

        run_ocr_pipeline_task.delay(
            file_path=tmp_path,
            document_id=doc.id,
            user_id=doc.user_id,
            project_id=doc.project_id,
        )

        doc.status = "processing"
        db.session.commit()

        return {
            "document_id": doc.id,
            "file_name": doc.file_name,
            "status": "processing",
        }

    except Exception as exc:
        current_app.logger.exception(
            "Failed to dispatch Celery OCR task for document %s", doc.id
        )
        doc.status = "failed"
        db.session.commit()

        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return {
            "document_id": doc.id,
            "file_name": doc.file_name,
            "status": "failed",
            "error": str(exc),
        }


@documents_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    """upload_document function."""

    files = request.files.getlist("files[]")

    user_id = get_jwt_identity()
    project_id = (request.form.get("project_id") or "").strip()

    if not files:
        return jsonify({"error": "No files provided"}), 400

    if not project_id:
        return jsonify({"error": "Field 'project_id' is required."}), 400

    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == user_id,
    )
    project = db.session.execute(stmt).scalars().all()

    if not project:
        return jsonify({"error": "Project not found."}), 404

    invalid = [
        f.filename for f in files if not f.filename or not allowed_file(f.filename)
    ]
    if invalid:
        return jsonify({"error": "Invalid or disallowed files", "files": invalid}), 400

    user_id = get_jwt_identity()
    docs_and_paths = []

    for file in files:
        ext = file.filename.rsplit(".", 1)[1].lower()

        fd, tmp_path = tempfile.mkstemp(suffix=f".{ext}")
        os.close(fd)

        file.save(tmp_path)

        with open(tmp_path, "rb") as local_file:
            key, file_url = upload_file_to_s3(local_file, file.filename)

        if not key:
            os.remove(tmp_path)
            return jsonify({"error": f"Failed to upload {file.filename} to S3"}), 500

        thumbnail_key = generate_thumbnail(tmp_path)

        doc = Document(
            user_id=user_id,
            project_id=project_id,
            file_name=file.filename,
            file_url=key,
            thumbnail_key=thumbnail_key,
            file_type=ext,
            file_size=os.path.getsize(tmp_path),
        )
        db.session.add(doc)
        docs_and_paths.append((doc, tmp_path))

    db.session.commit()

    results = [process_single(doc, path) for doc, path in docs_and_paths]

    succeeded = sum(1 for r in results if r["status"] == "processing")
    failed = len(results) - succeeded

    return (
        jsonify(
            {
                "summary": {
                    "total": len(results),
                    "succeeded": succeeded,
                    "failed": failed,
                },
                "documents": results,
            }
        ),
        207,
    )


@documents_bp.route("/delete", methods=["POST"])
@jwt_required()
def delete_documents():
    """delete_documents function."""
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    document_ids = data.get("document_ids")

    if not document_ids or not isinstance(document_ids, list):
        return jsonify({"error": "Field 'document_ids' (list) is required."}), 400

    stmt = select(Document).where(
        Document.id.in_(document_ids),
        Document.user_id == user_id,
    )
    docs = db.session.execute(stmt).scalars().all()

    found_ids = {doc.id for doc in docs}
    missing_ids = [doc_id for doc_id in document_ids if doc_id not in found_ids]

    results = []

    for doc_id in missing_ids:
        results.append(
            {
                "document_id": doc_id,
                "status": "error",
                "message": "Not found or not owned by user.",
            }
        )

    for doc in docs:
        result = {"document_id": doc.id, "file_name": doc.file_name}

        s3_ok = delete_s3_object(doc.file_url)
        thumb_ok = delete_s3_object(doc.thumbnail_key) if doc.thumbnail_key else True

        if not s3_ok or not thumb_ok:
            result["status"] = "error"
            result["message"] = "Failed to delete file from S3."
            results.append(result)
            continue

        try:
            db.session.delete(doc)
            db.session.commit()
            result["status"] = "deleted"
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(
                f"Failed to delete DB row for document {doc.id}"
            )
            result["status"] = "error"
            result["message"] = str(e)

        results.append(result)

    succeeded = sum(1 for r in results if r["status"] == "deleted")
    failed = len(results) - succeeded

    return (
        jsonify(
            {
                "summary": {
                    "total": len(results),
                    "succeeded": succeeded,
                    "failed": failed,
                },
                "documents": results,
            }
        ),
        207,
    )


@documents_bp.route("", methods=["GET"])
@jwt_required()
def get_project_documents():
    """
    Fetch all uploaded documents in specified project by currently logged-in user .
    Returns metadata and thumbnail URLs for grid/list preview displays.
    """
    try:
        current_user_id = get_jwt_identity()
        project_id = request.args.get("project_id")

        if not project_id:
            return (
                jsonify(
                    {"status": "error", "message": "Field 'project_id' is required."}
                ),
                400,
            )

        stmt = (
            select(Document)
            .where(
                Document.user_id == current_user_id, Document.project_id == project_id
            )
            .order_by(Document.created_at.desc())
        )
        documents = db.session.execute(stmt).scalars().all()

        documents_list = []
        for doc in documents:
            documents_list.append(
                {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "status": doc.status,
                    "thumbnail_url": generate_presigned_url(doc.thumbnail_key),
                    "created_at": doc.created_at.isoformat()
                    if doc.created_at
                    else None,
                    "updated_at": doc.updated_at.isoformat()
                    if doc.updated_at
                    else None,
                }
            )

        return jsonify(documents_list), 200

    except Exception as e:
        current_app.logger.exception(
            "GET /api/documents failed for user derived from JWT. Error: %s", e
        )
        return (
            jsonify(
                {
                    "error": "Failed to retrieve documents",
                    "details": str(e),
                }
            ),
            500,
        )


@documents_bp.route("/preview", methods=["GET"])
@jwt_required()
def get_user_documents_preview():
    """
    Returns the N most-recently uploaded documents for the current user.
    Useful for dashboard quick-preview widgets.
    Query param: limit (default 5)
    """
    try:
        current_user_id = get_jwt_identity()
        limit = request.args.get("limit", 5, type=int)

        stmt = (
            select(Document)
            .where(Document.user_id == current_user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        documents = db.session.execute(stmt).scalars().all()

        documents_list = []
        for doc in documents:
            documents_list.append(
                {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "status": doc.status,
                    "thumbnail_url": generate_presigned_url(doc.thumbnail_key),
                    "created_at": doc.created_at.isoformat()
                    if doc.created_at
                    else None,
                    "updated_at": doc.updated_at.isoformat()
                    if doc.updated_at
                    else None,
                }
            )

        return jsonify(documents_list), 200

    except Exception as e:
        current_app.logger.exception("GET /api/documents/preview failed. Error: %s", e)
        return (
            jsonify(
                {
                    "error": "Failed to retrieve document previews",
                    "details": str(e),
                }
            ),
            500,
        )


@documents_bp.route("/<string:document_id>", methods=["GET"])
@jwt_required()
def get_document(document_id):
    """Fetch a single document's metadata by ID (must belong to the current user)."""
    try:
        doc = get_user_document(document_id)

        if not doc:
            return (
                jsonify(
                    {
                        "error": "Document not found",
                        "details": f"No document with id '{document_id}' exists for this user.",
                    }
                ),
                404,
            )

        page_count = len(doc.pages) if doc.pages else 0

        return (
            jsonify(
                {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "status": doc.status,
                    "thumbnail_url": generate_presigned_url(doc.thumbnail_key),
                    "content_url": generate_presigned_url(doc.file_url),
                    "page_count": page_count,
                    "created_at": doc.created_at.isoformat()
                    if doc.created_at
                    else None,
                    "updated_at": doc.updated_at.isoformat()
                    if doc.updated_at
                    else None,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.exception(
            "GET /api/documents/%s failed. Error: %s", document_id, e
        )
        return (
            jsonify(
                {
                    "error": "Failed to fetch document",
                    "details": str(e),
                }
            ),
            500,
        )


MIME_MAP = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tiff": "image/tiff",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@documents_bp.route("/<string:document_id>/thumbnail", methods=["GET"])
@jwt_required()
def get_thumbnail_url(document_id):
    """get_thumbnail_url function."""
    try:
        doc = get_user_document(document_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        if not doc.thumbnail_key:
            return jsonify({"error": "Thumbnail not available"}), 404

        url = generate_presigned_url(doc.thumbnail_key, content_type="image/jpeg")
        return jsonify({"url": url}), 200

    except Exception as e:
        return (
            jsonify({"error": "Failed to generate thumbnail URL", "details": str(e)}),
            500,
        )


@documents_bp.route("/<string:document_id>/content", methods=["GET"])
@jwt_required()
def get_content_url(document_id):
    """get_content_url function."""
    try:
        doc = get_user_document(document_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        content_type = MIME_MAP.get(doc.file_type)
        url = generate_presigned_url(
            doc.file_url, inline=True, content_type=content_type
        )
        return jsonify({"url": url}), 200

    except Exception as e:
        return (
            jsonify({"error": "Failed to generate content URL", "details": str(e)}),
            500,
        )


@documents_bp.route("/<string:document_id>/text", methods=["GET"])
@jwt_required()
def get_document_text(document_id):
    """Return the raw OCR-extracted text for each page of a document."""
    try:
        current_user_id = get_jwt_identity()

        stmt = (
            select(Document)
            .where(
                Document.id == document_id,
                Document.user_id == current_user_id,
            )
            .options(selectinload(Document.pages))
        )
        doc = db.session.execute(stmt).scalar_one_or_none()

        if not doc:
            return (
                jsonify(
                    {
                        "error": "Document not found",
                        "details": f"No document with id '{document_id}' exists for this user.",
                    }
                ),
                404,
            )

        if doc.status != "ready":
            return (
                jsonify(
                    {
                        "error": "Document text not yet available",
                        "details": f"Document is currently in '{doc.status}' state. "
                        "Text is only available once processing is complete.",
                    }
                ),
                409,
            )

        pages = [
            {"page_number": page.page_number, "raw_text": page.raw_text}
            for page in sorted(doc.pages, key=lambda p: p.page_number)
        ]

        return (
            jsonify(
                {
                    "document_id": doc.id,
                    "pages": pages,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.exception(
            "GET /api/documents/%s/text failed. Error: %s", document_id, e
        )
        return (
            jsonify(
                {
                    "error": "Failed to fetch document text",
                    "details": str(e),
                }
            ),
            500,
        )
