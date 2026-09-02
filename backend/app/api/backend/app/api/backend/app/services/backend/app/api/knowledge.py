from fastapi import APIRouter, HTTPException

from app.services.knowledge_service import (
    get_all_knowledge,
    get_knowledge_by_id,
)

router = APIRouter()


@router.get("/knowledge")
def get_knowledge():
    return get_all_knowledge()


@router.get("/knowledge/{knowledge_id}")
def get_knowledge_object(knowledge_id: str):

    knowledge = get_knowledge_by_id(knowledge_id)

    if knowledge is None:
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge Object '{knowledge_id}' not found."
        )

    return knowledge