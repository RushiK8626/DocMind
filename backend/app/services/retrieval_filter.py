def build_chroma_filter(user_id: str, project_id: str | None = None) -> dict:
    """
    Builds a ChromaDB where-filter dict.
    ChromaDB requires $and to have at least 2 conditions — never pass it a single condition.
    """
    conditions = [{"user_id": {"$eq": user_id}}]

    if project_id and project_id.strip():
        conditions.append({"project_id": {"$eq": project_id}})

    return {"$and": conditions} if len(conditions) > 1 else conditions[0]


def build_bm25_filter(user_id: str, project_id: str | None = None) -> dict:
    """
    Returns kwargs to filter DB query for BM25 index construction.
    """
    filters = {"user_id": user_id}

    if project_id and project_id.strip():
        filters["project_id"] = project_id

    return filters