from typing import Optional

from app.models.retrieval import RetrievalResult
from app.services.knowledge_service import get_all_knowledge


def _calculate_relevance(knowledge: dict, query: str) -> int:
    """
    Calculate a deterministic relevance score for a knowledge object.

    Higher scores indicate a stronger textual match.
    """

    query = query.lower().strip()

    knowledge_id = str(knowledge.get("id", "")).lower()
    title = str(knowledge.get("title", "")).lower()
    domain = str(knowledge.get("domain", "")).lower()
    object_class = str(knowledge.get("object_class", "")).lower()

    score = 0

    if title == query:
        score += 100
    elif query in title:
        score += 50

    if query in knowledge_id:
        score += 30

    if query in domain:
        score += 20

    if query in object_class:
        score += 10

    return score


def _build_retrieval_result(
    knowledge: dict,
    relevance_score: Optional[int] = None,
) -> RetrievalResult:
    """
    Convert a knowledge object into a structured RetrievalResult.
    """

    return RetrievalResult(
        knowledge_id=knowledge.get("id", ""),
        title=knowledge.get("title", ""),
        status=knowledge.get("status", ""),
        domain=knowledge.get("domain", ""),
        object_class=knowledge.get("object_class", ""),
        relevance_score=relevance_score,
    )


def search_knowledge(
    query: Optional[str] = None,
    domain: Optional[str] = None,
    status: Optional[str] = None,
    object_class: Optional[str] = None,
):
    """
    Search and filter ClinRx knowledge objects.

    Parameters:
        query: Free-text search across id, title, domain, and object_class.
        domain: Filter by clinical domain.
        status: Filter by knowledge object status.
        object_class: Filter by knowledge object class.

    Returns:
        A list of structured RetrievalResult objects, ranked by relevance
        when a query is provided.
    """

    knowledge_objects = get_all_knowledge()
    matched_objects = []

    for knowledge in knowledge_objects:

        if query:
            search_text = " ".join(
                [
                    str(knowledge.get("id", "")),
                    str(knowledge.get("title", "")),
                    str(knowledge.get("domain", "")),
                    str(knowledge.get("object_class", "")),
                ]
            ).lower()

            if query.lower() not in search_text:
                continue

        if domain and knowledge.get("domain", "").lower() != domain.lower():
            continue

        if status and knowledge.get("status", "").lower() != status.lower():
            continue

        if (
            object_class
            and knowledge.get("object_class", "").lower()
            != object_class.lower()
        ):
            continue

        matched_objects.append(knowledge)

    results = []

    for knowledge in matched_objects:
        relevance_score = (
            _calculate_relevance(knowledge, query)
            if query
            else None
        )

        results.append(
            _build_retrieval_result(
                knowledge,
                relevance_score,
            )
        )

    if query:
        results.sort(
            key=lambda result: result.relevance_score or 0,
            reverse=True,
        )

    return results