"""Module ocr_tasks.py."""
from celery import shared_task
from app.services.ocr_service import OcrProcessingService
import logging
import os

logger = logging.getLogger('app')


ocr_service_instance = None


def get_ocr_service():
    """get_ocr_service function."""
    global ocr_service_instance
    if ocr_service_instance is None:
        logger.info("Initializing OcrProcessingService (loading models into memory)...")
        ocr_service_instance = OcrProcessingService()
    return ocr_service_instance


@shared_task(bind=True, max_retries=3)
def run_ocr_pipeline_task(
    self, file_path: str, document_id: str, user_id: str, project_id: str
):
    """
    Celery background worker task for processing complex documents via Docling + PaddleOCR.
    """
    logger.info(f"Starting OCR task {self.request.id} for document: {document_id}")

    try:

        ocr_service = get_ocr_service()

        success = ocr_service.run(
            file_path=file_path,
            document_id=document_id,
            user_id=user_id,
            project_id=project_id,
        )

        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temp file after success: {file_path}")

        return {"status": "completed", "document_id": document_id}

    except Exception as exc:
        if self.request.retries >= self.max_retries:

            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(
                    f"Cleaned up temp file after max retries exhausted: {file_path}"
                )
            logger.error(
                f"Task failed permanently for document {document_id}. Error: {str(exc)}"
            )
            raise
        else:
            logger.error(
                f"Task failed for document {document_id}. Retrying... Error: {str(exc)}"
            )

            raise self.retry(exc=exc, countdown=60)
