"""
Wraps ChromaDB — handles client init, collection access, and similarity search.
Assumes embeddings were already stored during ingestion 
"""

from flask import current_app
import logging
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger('app')


_chroma_service_instance: "ChromaService | None" = None


def get_chroma_service() -> "ChromaService":
    """
    Returns the module-level ChromaService singleton.
    """
    global _chroma_service_instance
    if _chroma_service_instance is None:
        _chroma_service_instance = ChromaService()
    return _chroma_service_instance


class ChromaService:
    """
    Singleton-style service for ChromaDB retrieval.

    If your ingestion pipeline stored raw text with embeddings computed by
    chromadb's default EF, set use_default_ef=True (default).
    """

    def __init__(
        self,
        chroma_host: str | None = None,
        chroma_port: int | None = None,
        persist_path: str | None = None,
        collection_name: str | None = None,
        embedding_model: str | None = None,
    ):
        """__init__ function."""
        from flask import current_app

        chroma_host = chroma_host or current_app.config.get("CHROMA_HOST", "localhost")
        chroma_port = chroma_port or current_app.config.get("CHROMA_PORT", 8000)
        persist_path = persist_path or current_app.config["CHROMA_PERSIST_DIR"]
        collection_name = (
            collection_name or current_app.config["CHROMA_COLLECTION_NAME"]
        )

        self._client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

        ef_model = embedding_model or "all-MiniLM-L6-v2"

        from chromadb import Documents, EmbeddingFunction, Embeddings

        class CpuPyTorchEmbeddingFunction(EmbeddingFunction):
            """CpuPyTorchEmbeddingFunction class."""

            def __init__(self, model_name: str):
                """__init__ function."""
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(model_name, device="cpu")

            def __call__(self, input: Documents) -> Embeddings:
                """__call__ function."""
                return self._model.encode(input, convert_to_numpy=True).tolist()

        ef = CpuPyTorchEmbeddingFunction(model_name=ef_model)
        logger.info(f"Using CPU-bound PyTorch EF: {ef_model}")

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=ef,
        )
        logger.info(
            f"ChromaDB ready — collection '{collection_name}' "
            f"({self._collection.count()} docs) at {persist_path}"
        )

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Add new documents to the collection (fails on duplicate IDs).

        Args:
            documents: List of raw text chunks to embed and store.
            metadatas: Optional list of metadata dicts (one per document).
                       e.g. [{"source": "file.pdf", "page": 1}, ...]
            ids:       Optional list of unique string IDs.
                       Auto-generated as "doc-0", "doc-1", … if not provided.

        Returns:
            { "added": int, "total": int }

        Raises:
            ValueError: if list lengths are mismatched.
            chromadb.errors.IDAlreadyExistsError: on duplicate IDs — use
            upsert_documents() if you want add-or-update semantics.
        """
        if not documents:
            return {"added": 0, "total": self._collection.count()}

        if metadatas and len(metadatas) != len(documents):
            raise ValueError(
                f"metadatas length ({len(metadatas)}) must match documents length ({len(documents)})"
            )
        if ids and len(ids) != len(documents):
            raise ValueError(
                f"ids length ({len(ids)}) must match documents length ({len(documents)})"
            )

        if not ids:
            current_count = self._collection.count()
            ids = [f"doc-{current_count + i}" for i in range(len(documents))]

        safe_metadatas = []
        if metadatas:
            for meta in metadatas:
                cleaned = {k: v for k, v in meta.items() if v is not None}
                safe_metadatas.append(cleaned)
        else:
            safe_metadatas = [{}] * len(documents)

        self._collection.add(
            documents=documents,
            metadatas=safe_metadatas,
            ids=ids,
        )

        total = self._collection.count()
        logger.info(f"✅ Added {len(documents)} documents — collection total: {total}")
        return {"added": len(documents), "total": total}

    def upsert_documents(
        self,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Add-or-update documents (safe to call with existing IDs).
        Identical signature to add_documents() — use this for re-ingestion.
        """
        if not documents:
            return {"upserted": 0, "total": self._collection.count()}

        if metadatas and len(metadatas) != len(documents):
            raise ValueError(
                f"metadatas length ({len(metadatas)}) must match documents length ({len(documents)})"
            )
        if ids and len(ids) != len(documents):
            raise ValueError(
                f"ids length ({len(ids)}) must match documents length ({len(documents)})"
            )

        if not ids:
            current_count = self._collection.count()
            ids = [f"doc-{current_count + i}" for i in range(len(documents))]

        safe_metadatas = []
        if metadatas:
            for meta in metadatas:
                cleaned = {k: v for k, v in meta.items() if v is not None}
                safe_metadatas.append(cleaned)
        else:
            safe_metadatas = [{}] * len(documents)

        self._collection.upsert(
            documents=documents,
            metadatas=safe_metadatas,
            ids=ids,
        )

        total = self._collection.count()
        logger.info(
            f"🔄 Upserted {len(documents)} documents — collection total: {total}"
        )
        return {"upserted": len(documents), "total": total}

    def delete_documents(self, ids: list[str]) -> dict[str, Any]:
        """Delete documents by ID list."""
        self._collection.delete(ids=ids)
        total = self._collection.count()
        logger.info(f"🗑️  Deleted {len(ids)} documents — collection total: {total}")
        return {"deleted": len(ids), "total": total}

    def delete(self, where: dict | None = None, ids: list[str] | None = None) -> None:
        """Delete documents from collection using a filter or IDs."""
        self._collection.delete(where=where, ids=ids)
        total = self._collection.count()
        logger.info(
            f"🗑️ Deleted documents with filter {where} or ids {ids} — collection total: {total}"
        )

    def collection_info(self) -> dict:
        """collection_info function."""
        from flask import current_app

        return {
            "name": self._collection.name,
            "count": self._collection.count(),
            "path": current_app.config["CHROMA_PERSIST_DIR"],
        }

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        where: dict | None = None,
    ) -> list[dict[str, Any]]:
        """retrieve function."""
        from flask import current_app

        top_k = top_k or current_app.config["TOP_K_RESULTS"]
        """
        Query the collection and return top_k most similar chunks.

        Returns a list of dicts:
            {
                "id":       str,
                "document": str,
                "metadata": dict,
                "distance": float,   # lower = more similar
            }
        """
        if not query.strip():
            return []

        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": min(top_k, self._collection.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        try:
            results = self._collection.query(**kwargs)
        except Exception as e:
            if "n_results" in str(e) or "number of elements" in str(e):
                logger.warning(f"No matching chunks for query with filter {where}")
                return []
            raise

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        chunks = [
            {
                "id": ids[i],
                "document": documents[i],
                "metadata": metadatas[i],
                "distance": round(distances[i], 4),
            }
            for i in range(len(ids))
        ]

        logger.debug(f"Retrieved {len(chunks)} chunks for query: '{query[:60]}…'")
        return chunks

    def collection_info(self) -> dict:
        """collection_info function."""
        from flask import current_app

        return {
            "name": self._collection.name,
            "count": self._collection.count(),
            "path": current_app.config["CHROMA_PERSIST_DIR"],
        }
