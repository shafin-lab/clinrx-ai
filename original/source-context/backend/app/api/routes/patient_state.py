"""Bounded recorded-state HTTP adapter."""
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from app.api.schemas.common import DTO, AwareTimestamp
from app.api.schemas.patient_state import PatientStateViewResponse
from app.api.routes.temporal_reviews import product_service, clinical_metadata, PREFIX
from app.api.middleware import no_store

router = APIRouter(prefix=PREFIX, dependencies=[Depends(no_store)])


class StateQuery(DTO):
    review_start: AwareTimestamp
    review_end: AwareTimestamp


@router.get('/state', response_model=PatientStateViewResponse)
def state(patient_id: str, encounter_id: str, query: Annotated[StateQuery, Query()], response: Response,
          service=Depends(product_service)):
    clinical_metadata(response, service)
    return service.state(patient_id, encounter_id, query.review_start, query.review_end)
