"""Process health only; no database or clinical work."""
from typing import Literal
from fastapi import APIRouter
from app.api.schemas.common import DTO

router = APIRouter()


class HealthResponse(DTO):
    status: Literal['ok'] = 'ok'
    service: Literal['clinrx-api'] = 'clinrx-api'


@router.get('/health', response_model=HealthResponse)
def health():
    return HealthResponse()
