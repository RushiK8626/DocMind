"""Module for BM25 text search and caching."""
import re
from rank_bm25 import BM25Okapi

from functools import lru_cache


class BM25Index:
    """An index for performing BM25-based keyword search on document corpora."""
    def __init__(self, corpus: list[dict]):
        """
        corpus: list of {
            "id":                 layout_element_id,
            "content":            str,
            "page_number":        int,
            "layout_element_id":  str,
            "document_id":        str,
        }
        """
        self._corpus  = corpus
        self._index   = BM25Okapi([_tokenize(c["content"]) for c in corpus])

    def retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        """Retrieve top k document chunks matching the query using BM25."""
        tokens = _tokenize(query)
        scores = self._index.get_scores(tokens)

        ranked = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:top_k]

        results = []
        for rank, (idx, score) in enumerate(ranked):
            if score == 0:
                continue
            entry = self._corpus[idx]
            results.append({
                "id":                 entry["id"],
                "document":           entry["content"],
                "metadata": {
                    "page_number":        entry["page_number"],
                    "layout_element_id":  entry["layout_element_id"],
                    "document_id":        entry["document_id"],
                },
                "bm25_score": score,
                "bm25_rank":  rank + 1,
            })

        return results


def build_bm25_index(user_id: str, project_id: str | None = None) -> "BM25Index":
    """
    Load LayoutElements from DB filtered by user/project and build BM25 index.
    Called once per request (or cached — see Step 4).
    """
    from app.models import LayoutElement, Page, Document

    query = (
        LayoutElement.query
        .join(Page, Page.id == LayoutElement.page_id)
        .join(Document, Document.id == Page.document_id)
        .filter(Document.user_id == user_id)
    )
    if project_id:
        query = query.filter(Document.project_id == project_id)

    elements = query.all()

    corpus = [
        {
            "id":                e.id,
            "content":           e.content,
            "page_number":       e.page.page_number,
            "layout_element_id": e.id,
            "document_id":       e.page.document_id,
        }
        for e in elements
        if e.content and e.content.strip()
    ]

    return BM25Index(corpus)

@lru_cache(maxsize=64)
def get_cached_bm25_index(user_id: str, project_id: str | None) -> "BM25Index":
    """Retrieve or build the cached BM25 index for the specified user and project."""
    return build_bm25_index(user_id=user_id, project_id=project_id)

def invalidate_bm25_cache(user_id: str, project_id: str | None):
    """Invalidate the cached BM25 index for a user and project."""
    get_cached_bm25_index.cache_clear() 
    
def _tokenize(text: str) -> list[str]:
    """Tokenize a string by splitting on word characters and converting to lowercase."""
    return re.findall(r'\w+', text.lower())