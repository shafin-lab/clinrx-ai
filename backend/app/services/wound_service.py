"""Exact source ownership and append-only admission for wound timeline events."""
from app.models.clinical.wound import WoundRecord
from app.services.recorded_source_service import append_recorded_source, lookup_recorded_source, require_source_identity


def save_wound_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    require_source_identity(record, WoundRecord, 'wound-', 'wound')
    return append_recorded_source(service, repo, record)


def lookup_wound_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    require_source_identity(record, WoundRecord, 'wound-', 'wound')
    return lookup_recorded_source(service, repo, record)
