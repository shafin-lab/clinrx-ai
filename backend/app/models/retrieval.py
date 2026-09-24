from pydantic import BaseModel
from typing import Optional


class RetrievalResult(BaseModel):
    knowledge_id: str
    title: str
    status: str
    domain: str
    object_class: str
    relevance_score: Optional[int] = None