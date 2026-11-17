"""Exact source ownership and append-only admission for endocrine timeline events."""
from app.models.clinical.endocrine import EndocrineRecord
from app.services.recorded_source_service import append_recorded_source, lookup_recorded_source, require_source_identity


def save_endocrine_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    require_source_identity(record, EndocrineRecord, 'endo-', 'endocrine')
    return append_recorded_source(service, repo, record)


def lookup_endocrine_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    require_source_identity(record, EndocrineRecord, 'endo-', 'endocrine')
    return lookup_recorded_source(service, repo, record)
