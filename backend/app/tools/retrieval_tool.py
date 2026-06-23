"""Module retrieval_tool.py."""
import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.services.chroma_service import get_chroma_service

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
        filter_conditions = [{"user_id": user_id}]
        if project_id:
            filter_conditions.append({"project_id": project_id})

        where_filter = (
            filter_conditions[0]
            if len(filter_conditions) == 1
            else {"$and": filter_conditions}
        )

        chunks = get_chroma_service().retrieve(
            query=query, top_k=top_k, where=where_filter
        )

        if not chunks:
            return []

        formatted = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk.get("metadata", {})
            src = meta.get("source", meta.get("filename", chunk["id"]))
            formatted.append(
                {
                    "chunk_index": i,
                    "source": src,
                    "similarity_distance": chunk["distance"],
                    "content": chunk["document"],
                }
            )

        logger.debug(f"RetrievalTool returned {len(chunks)} chunks")
        return formatted

    return retriever
