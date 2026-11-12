"""Admission for append-only neurological sources in the synthetic RF2 repository."""
from app.models.clinical.neurological import NeurologicalRecord
from app.services.recorded_source_service import append_recorded_source, lookup_recorded_source, require_source_identity


def save_neurological_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    require_source_identity(record, NeurologicalRecord, 'neuro-', 'neurological')
    return append_recorded_source(service, repo, record)


def lookup_neurological_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    require_source_identity(record, NeurologicalRecord, 'neuro-', 'neurological')
    return lookup_recorded_source(service, repo, record)
