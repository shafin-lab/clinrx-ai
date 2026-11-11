"""Admission for append-only gastrointestinal sources in the shared synthetic repository."""
from app.demo.authoring import TARGET
from app.models.clinical.gastrointestinal import GastrointestinalRecord
from app.persistence.errors import UnsupportedOperation
from app.services.recorded_source_service import append_recorded_source, lookup_recorded_source, require_source_identity


def save_gastrointestinal_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    require_source_identity(record, GastrointestinalRecord, 'gi-', 'gastrointestinal')
    return append_recorded_source(service, repo, record)


def lookup_gastrointestinal_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    if record.binding.target != TARGET:
        raise UnsupportedOperation('foreign source scope')
    return lookup_recorded_source(service, repo, record)
