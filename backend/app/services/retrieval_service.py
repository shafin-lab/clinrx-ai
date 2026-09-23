from typing import Optional

from app.services.knowledge_service import get_all_knowledge


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
        A list of matching knowledge objects.
    """

    knowledge_objects = get_all_knowledge()
    results = []

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

        results.append(knowledge)

    return results