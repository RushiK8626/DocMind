"""Module ocr_service.py."""
import os
import uuid
from typing import List
from PIL import Image
import numpy as np
from decimal import Decimal

from app.extensions import db
from app.models import Page, LayoutElement, ElementType

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat, DocItemLabel
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.datamodel.pipeline_options import AcceleratorOptions, AcceleratorDevice


from .chroma_service import get_chroma_service


class OcrProcessingService:
    """OcrProcessingService class."""

    def __init__(self):
        """__init__ function."""

        pipeline_options = PdfPipelineOptions(
            do_ocr=True,
            ocr_options=EasyOcrOptions(
                lang=["en", "hi", "mr"], confidence_threshold=0.5
            ),
        )

        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.do_formula_enrichment = True

        pipeline_options.accelerator_options = AcceleratorOptions(
            device=AcceleratorDevice.CUDA, num_threads=os.cpu_count() or 4
        )

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def run(
        self, file_path: str, document_id: str, user_id: str, project_id: str
    ) -> bool:
        """
        Executes layout-aware parsing, pushes vectors to Chroma DB,
        and updates relational database instances.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Target document not found at: {file_path}")

        try:

            from app.models import Document

            doc = db.session.get(Document, document_id)
            if doc:
                doc.status = "processing"
                db.session.commit()

            conversion_result = self.converter.convert(file_path)
            docling_doc = conversion_result.document

            base_metadata = {
                "document_id": document_id,
                "user_id": user_id,
                "project_id": project_id,
            }

            chroma_texts = []
            chroma_metadatas = []
            chroma_ids = []

            for page_no, page_item in docling_doc.pages.items():

                page_texts = [
                    item.text
                    for item, _ in docling_doc.iterate_items()
                    if hasattr(item, "prov")
                    and any(p.page_no == page_no for p in item.prov)
                    and hasattr(item, "text")
                ]
                raw_page_text = "\n".join(page_texts) if page_texts else ""

                db_page = Page(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    page_number=page_no,
                    raw_text=raw_page_text,
                    width=Decimal(str(page_item.size.width))
                    if page_item.size
                    else None,
                    height=Decimal(str(page_item.size.height))
                    if page_item.size
                    else None,
                    image_url=None,
                )
                db.session.add(db_page)

                print(raw_page_text)

                for item, _ in docling_doc.iterate_items():

                    if not hasattr(item, "prov") or not any(
                        p.page_no == page_no for p in item.prov
                    ):
                        continue

                    prov = next((p for p in item.prov if p.page_no == page_no), None)
                    if not prov or not prov.bbox:
                        continue

                    if item.label == DocItemLabel.TABLE:
                        elem_type = ElementType.TABLE_CELL

                        content = (
                            item.export_to_markdown(doc=docling_doc)
                            if hasattr(item, "export_to_markdown")
                            else getattr(item, "text", "")
                        )
                    else:
                        elem_type = ElementType.TEXT
                        content = getattr(item, "text", "")

                    if not content:
                        continue

                    p_width = float(page_item.size.width) if page_item.size else 1.0
                    p_height = float(page_item.size.height) if page_item.size else 1.0

                    box_left = max(0.0, min(1.0, float(prov.bbox.l) / p_width))
                    box_top = max(0.0, min(1.0, float(prov.bbox.t) / p_height))
                    box_width = max(
                        0.0, min(1.0, float(prov.bbox.r - prov.bbox.l) / p_width)
                    )
                    box_height = max(
                        0.0, min(1.0, float(prov.bbox.b - prov.bbox.t) / p_height)
                    )

                    db_element = LayoutElement(
                        id=str(uuid.uuid4()),
                        page_id=db_page.id,
                        element_type=elem_type,
                        content=content,
                        box_left=Decimal(f"{box_left:.4f}"),
                        box_top=Decimal(f"{box_top:.4f}"),
                        box_width=Decimal(f"{box_width:.4f}"),
                        box_height=Decimal(f"{box_height:.4f}"),
                        confidence=Decimal("0.950"),
                    )
                    db.session.add(db_element)

                    chroma_texts.append(content)

                    chunk_metadata = base_metadata.copy()
                    chunk_metadata.update(
                        {
                            "page_number": page_no,
                            "element_type": elem_type.value,
                            "layout_element_id": db_element.id,
                        }
                    )
                    chroma_metadatas.append(chunk_metadata)
                    chroma_ids.append(db_element.id)

            if chroma_texts:
                get_chroma_service().add_documents(
                    documents=chroma_texts, metadatas=chroma_metadatas, ids=chroma_ids
                )

            if doc:
                pages_meta = []
                for p_no, page_item in docling_doc.pages.items():
                    elem_count = sum(
                        1 for m in chroma_metadatas if m.get("page_number") == p_no
                    )
                    pages_meta.append(
                        {"page_number": p_no, "element_count": elem_count}
                    )

                doc.extracted_json = {
                    "total_pages": len(docling_doc.pages),
                    "pages": pages_meta,
                }
                doc.status = "ready"

            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            try:
                from app.models import Document

                doc = db.session.get(Document, document_id)
                if doc:
                    doc.status = "failed"
                    db.session.commit()
            except Exception as db_err:
                print(f"Failed to update document status to failed: {db_err}")

            print(f"OCR Pipeline processing failure: {str(e)}")
            raise e
