"""Module for hybrid retrieval combining semantic and BM25 search."""
from app.services.bm25_service import get_cached_bm25_index
from app.services.chroma_service import get_chroma_service
from app.services.retrieval_filter import build_chroma_filter, build_bm25_filter


def _rrf_score(rank: int, k: int = 60) -> float:
    """Calculate the Reciprocal Rank Fusion (RRF) score for a given rank."""
    return 1.0 / (k + rank)


def hybrid_retrieve(
    query:      str,
    user_id:    str,
    project_id: str | None = None,
    top_k:      int = 5,
) -> list[dict]:
    """Retrieve documents using hybrid search (semantic + BM25) and RRF fusion."""

    fetch_k = top_k * 2   # fetch more from each source before re-ranking

    #  Semantic retrieval 
    chroma_filter  = build_chroma_filter(user_id, project_id)   # centralized
    semantic_chunks = get_chroma_service().retrieve(
        query=query, top_k=fetch_k, where=chroma_filter
    )
    for rank, chunk in enumerate(semantic_chunks):
        chunk["semantic_rank"] = rank + 1

    #  BM25 retrieval 
    bm25_filter  = build_bm25_filter(user_id, project_id)       # centralized
    bm25_index   = get_cached_bm25_index(
        user_id=bm25_filter["user_id"],
        project_id=bm25_filter.get("project_id"),
    )
    bm25_chunks  = bm25_index.retrieve(query=query, top_k=fetch_k)
    for rank, chunk in enumerate(bm25_chunks):
        chunk["bm25_rank"] = rank + 1

    #  RRF Fusion 
    scores:     dict[str, float] = {}
    all_chunks: dict[str, dict]  = {}

    for chunk in semantic_chunks:
        eid            = chunk.get("metadata", {}).get("layout_element_id")
        if not eid:
            continue
        scores[eid]    = scores.get(eid, 0.0) + _rrf_score(chunk["semantic_rank"])
        all_chunks[eid] = chunk

    for chunk in bm25_chunks:
        eid            = chunk.get("metadata", {}).get("layout_element_id")
        if not eid:
            continue
        scores[eid]    = scores.get(eid, 0.0) + _rrf_score(chunk["bm25_rank"])
        if eid not in all_chunks:
            all_chunks[eid] = chunk

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    results = []
    for eid, rrf_score in ranked:
        chunk = all_chunks[eid]
        chunk["rrf_score"] = round(rrf_score, 6)
        results.append(chunk)

    return results