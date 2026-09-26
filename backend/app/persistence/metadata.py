"""Storage metadata contracts; no context reconstruction is implemented here."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.clinical.common import Reference, require_kind


class StorageMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')


class IngestionMetadata(StorageMetadata):
    repository_id: UUID
    ingestion_sequence: Annotated[int, Field(strict=True, gt=0)]
    ingested_at: AwareDatetime
    payload_version: Literal[1] = 1


class RepositoryCutoff(StorageMetadata):
    """Fact-ingestion prefix in ONE repository, not a clinical event-time cutoff."""
    repository_id: UUID
    fact_watermark: Annotated[int, Field(strict=True, ge=0)]
    captured_at: AwareDatetime


class ReconstructionMetadata(StorageMetadata):
    """Reserved future snapshot envelope; no policy implementation/approval implied."""
    reconstruction_policy: Reference
    repository_cutoff: RepositoryCutoff
    clinical_as_of: AwareDatetime | None = None
    knowledge_cutoff: AwareDatetime

    @model_validator(mode='after')
    def explicit_policy(self):
        require_kind(self.reconstruction_policy, 'reconstruction_policy')
        return self
