"""Module retrieval_tool.py."""
import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.services.hybrid_retrieval import hybrid_retrieve

logger = logging.getLogger('app')


class RetrievalInput(BaseModel):
    """RetrievalInput class."""

    query: str = Field(
        ..., description="The search query to retrieve relevant documents for."
    )


def create_retrieval_tool(user_id: str, project_id: str):
    """create_retrieval_tool function."""

    @tool("retrieve_documents", args_schema=RetrievalInput)
    def retriever(query: str) -> list[dict]:
        """
        Retrieves relevant documents from the knowledge base.
        """
        from flask import current_app

        top_k = current_app.config["TOP_K_RESULTS"]
        top_k = max(1, min(top_k, 10))
        
        chunks = hybrid_retrieve(                         
            query=query,
            user_id=user_id,
            project_id=project_id,
            top_k=top_k,
        )

        if not chunks:
            return []

        formatted = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk.get("metadata", {})
            formatted.append({
                "chunk_index":        i,
                "content":            chunk["document"],
                "page_number":        meta.get("page_number"),
                "layout_element_id":  meta.get("layout_element_id"),
                "element_type":       meta.get("element_type"),
                "rrf_score":          chunk.get("rrf_score"),
            })

        logger.debug(f"RetrievalTool returned {len(chunks)} chunks")
        return formatted

    return retriever
