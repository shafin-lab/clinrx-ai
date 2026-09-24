from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services.knowledge_service import (
    get_all_knowledge,
    get_knowledge_by_id,
)
from app.services.retrieval_service import search_knowledge


router = APIRouter()


@router.get("/knowledge")
def get_knowledge():
    return get_all_knowledge()


@router.get("/knowledge/search")
def search_knowledge_objects(
    q: Optional[str] = None,
    domain: Optional[str] = None,
    status: Optional[str] = None,
    object_class: Optional[str] = None,
):
    return search_knowledge(
        query=q,
        domain=domain,
        status=status,
        object_class=object_class,
    )


@router.get("/knowledge/{knowledge_id}")
def get_knowledge_object(knowledge_id: str):
    knowledge = get_knowledge_by_id(knowledge_id)

    if knowledge is None:
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge Object '{knowledge_id}' not found."
        )

    return knowledge
