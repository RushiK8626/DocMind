"""Module file_service.py."""
import os
import io
import uuid
from PIL import Image
from docx2pdf import convert
from pdf2image import convert_from_path

from flask import current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import select

from app.models.document import Document
from app.extensions import db
from app import extensions

UPLOAD_THUMBNAILS_DIR = "/tmp/multimodal_uploads_thumbnails"
os.makedirs(UPLOAD_THUMBNAILS_DIR, exist_ok=True)


def get_user_document(document_id):
    """get_user_document function."""
    current_user_id = get_jwt_identity()

    stmt = select(Document).where(
        Document.id == document_id, Document.user_id == current_user_id
    )

    return db.session.execute(stmt).scalar_one_or_none()


def generate_thumbnail(file_path: str, thumbnail_size=(300, 400)) -> str | None:
    """
    Generates a lightweight JPG thumbnail for PDF, PNG, JPG, JPEG, TIFF, and DOCX files.
    Returns the S3 URL of the uploaded thumbnail, or None if failed.
    """
    filename = os.path.basename(file_path)
    file_name_without_ext, ext = os.path.splitext(filename)
    ext = ext.lower().replace(".", "")

    thumb_filename = f"thumb_{file_name_without_ext}.jpg"
    temp_pdf_path = None
    img = None

    try:

        if ext == "docx":
            temp_pdf_path = os.path.join(
                UPLOAD_THUMBNAILS_DIR, f"temp_{file_name_without_ext}.pdf"
            )
            convert(file_path, temp_pdf_path)
            file_path = temp_pdf_path
            ext = "pdf"

        if ext == "pdf":
            pages = convert_from_path(file_path, first_page=1, last_page=1)
            if not pages:
                return None
            img = pages[0].convert("RGB")

        elif ext in ["png", "jpg", "jpeg", "tiff", "tif"]:
            img = Image.open(file_path)
            if img.mode in ("RGBA", "P", "CMYK"):
                img = img.convert("RGB")

        else:
            print(f"Unsupported file extension: {ext}")
            return None

        img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        key, _url = upload_file_to_s3(buffer, thumb_filename)
        return key

    except Exception as e:
        print(f"Error generating thumbnail for {filename}: {e}")
        return None

    finally:

        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        if img:
            img.close()


def upload_file_to_s3(file_obj, filename):
    """upload_file_to_s3 function."""
    if extensions.s3_client is None:
        current_app.logger.error(
            "S3 client is not initialised. Ensure init_s3(app) is called in create_app()."
        )
        return None, None

    key = f"documents/{uuid.uuid4()}_{filename}"

    try:
        extensions.s3_client.upload_fileobj(
            file_obj,
            current_app.config["AWS_S3_BUCKET"],
            key,
        )
    except Exception as e:
        current_app.logger.error("Failed to upload file to S3: %s", e)
        return None, None

    url = (
        f"https://{current_app.config['AWS_S3_BUCKET']}.s3."
        f"{current_app.config['AWS_REGION']}.amazonaws.com/{key}"
    )

    return key, url


def delete_s3_object(key):
    """delete_s3_object function."""
    if not key:
        return True
    if extensions.s3_client is None:
        current_app.logger.error(
            "S3 client is not initialised. Ensure init_s3(app) is called in create_app()."
        )
        return False
    try:
        extensions.s3_client.delete_object(
            Bucket=current_app.config["AWS_S3_BUCKET"],
            Key=key,
        )
        return True
    except Exception as e:
        current_app.logger.error("Failed to delete file from S3: %s", e)
        return False


def generate_presigned_url(
    s3_key: str | None,
    expiry_seconds: int = 3600,
    inline: bool = False,
    content_type: str | None = None,
) -> str | None:
    """
    Generates a temporary pre-signed URL for a private S3 object.
    Returns None if s3_key is empty/None (e.g. thumbnail generation failed).
    Default expiry: 1 hour.
    """
    if not s3_key:
        current_app.logger.warning(
            "generate_presigned_url called with empty s3_key – returning None"
        )
        return None

    if extensions.s3_client is None:
        current_app.logger.error(
            "S3 client is not initialised. Ensure init_s3(app) is called in create_app()."
        )
        return None

    try:
        params = {"Bucket": current_app.config["AWS_S3_BUCKET"], "Key": s3_key}

        if inline:
            params["ResponseContentDisposition"] = "inline"
        if content_type:
            params["ResponseContentType"] = content_type

        url = extensions.s3_client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiry_seconds,
        )
        return url
    except Exception as exc:
        current_app.logger.error(
            "Failed to generate presigned URL for key '%s': %s", s3_key, exc
        )
        return None
