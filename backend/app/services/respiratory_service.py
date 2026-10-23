"""Admission for append-only respiratory sources in the shared synthetic repository."""
from hashlib import sha256
from app.demo.authoring import TARGET, EvidenceConflict
from app.models.clinical.respiratory import RespiratoryRecord
from app.persistence.canonical import canonical_payload
from app.persistence.errors import UnsupportedOperation
from app.models.clinical.recorded_v2 import instant


def available_by(record, end):
    """Both issued and available bounds must fit the historical review."""
    for point in (record.times.available, record.times.reported):
        at=point.upper or point.anchor
        if at is not None and instant(at)>instant(end):return False
    return True


def save_respiratory_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    if not isinstance(record, RespiratoryRecord) or record.binding.target!=TARGET or record.origin not in ('observed','reported'):
        raise UnsupportedOperation('respiratory record must be a typed observed or reported record in this synthetic encounter')
    owner='resp-'+sha256((record.source_identity.issuer_namespace+'\0'+record.source_identity.source_report_id).encode()).hexdigest()[:32]
    if record.id!=owner or record.revision!=record.source_identity.source_version:
        raise UnsupportedOperation('respiratory owner and revision must preserve exact source identity/version')
    accounting=service.accounting();cutoff=repo.capture_cutoff()
    rows=service.history_rows(repo,cutoff,accounting,record.reference)
    exact=next((row for row in rows if row.fact.reference==record.reference),None)
    if exact:
        if canonical_payload(exact.fact)!=canonical_payload(record):raise EvidenceConflict()
        return service.evidence(repo,exact,cutoff,accounting)
    # Exact source links may point to any original domain, but never another scope.
    for reference in record.linked_sources:repo.load_fact(reference,target=TARGET)
    prior=[row for row in rows if isinstance(row.fact,RespiratoryRecord)]
    if not prior:
        if record.supersedes is not None or record.change_state!='original':raise EvidenceConflict()
        stored=repo.append_fact(record,target=TARGET)
    else:
        terminal=prior[-1].fact
        identity=record.source_identity;previous=terminal.source_identity
        if (record.supersedes!=terminal.reference or record.change_state=='original' or record.category!=terminal.category
            or (identity.issuer_namespace,identity.source_report_id,identity.accession_id)!=(previous.issuer_namespace,previous.source_report_id,previous.accession_id)):
            raise EvidenceConflict()
        stored=repo.append_revision(record,target=TARGET)
    return service.evidence(repo,stored,repo.capture_cutoff(),accounting)
