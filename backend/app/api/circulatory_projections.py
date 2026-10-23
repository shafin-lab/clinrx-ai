"""Complete retained M7 provenance; no clinical reads or recomputation."""
from app.api.schemas.circulatory import CirculatoryExecutionResponse

def execution(stored):
    record=stored.record
    content=record.decision.released_content
    return CirculatoryExecutionResponse(execution_id=record.request.execution_id,record=record,
        ingested_at=stored.ingested_at,statement=content.content if content else None)
