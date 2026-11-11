"""Admission for append-only reproductive sources in the synthetic RF2 repository."""
from app.models.clinical.reproductive import ReproductiveRecord
from app.services.recorded_source_service import append_recorded_source, lookup_recorded_source, require_source_identity


def save_reproductive_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    require_source_identity(record, ReproductiveRecord, 'repro-', 'reproductive')
    return append_recorded_source(service, repo, record)


def lookup_reproductive_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    require_source_identity(record, ReproductiveRecord, 'repro-', 'reproductive')
    return lookup_recorded_source(service, repo, record)
