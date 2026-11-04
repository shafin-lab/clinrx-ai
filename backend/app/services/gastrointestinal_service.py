"""Admission for append-only gastrointestinal sources in the shared synthetic repository."""
from hashlib import sha256
from app.demo.authoring import TARGET, EvidenceConflict
from app.models.clinical.gastrointestinal import GastrointestinalRecord
from app.persistence.canonical import canonical_payload
from app.persistence.errors import UnsupportedOperation
def save_gastrointestinal_record(service, repo, repository, record):
    service.require_repo(repo, repository)
    if not isinstance(record, GastrointestinalRecord) or record.binding.target!=TARGET or record.origin not in ('observed','reported'):
        raise UnsupportedOperation('gastrointestinal record must be a typed observed or reported record in this synthetic encounter')
    owner='gi-'+sha256((record.source_identity.issuer_namespace+'\0'+record.source_identity.source_report_id).encode()).hexdigest()[:32]
    if record.id!=owner or record.revision!=record.source_identity.source_version:
        raise UnsupportedOperation('gastrointestinal owner and revision must preserve exact source identity/version')
    accounting=service.accounting();cutoff=repo.capture_cutoff()
    rows=service.history_rows(repo,cutoff,accounting,record.reference)
    exact=next((row for row in rows if row.fact.reference==record.reference),None)
    if exact:
        if canonical_payload(exact.fact)!=canonical_payload(record):raise EvidenceConflict()
        return service.evidence(repo,exact,cutoff,accounting)
    # Exact source links may point to any original domain, but never another scope.
    for reference in record.linked_sources:repo.load_fact(reference,target=TARGET)
    prior=[row for row in rows if isinstance(row.fact,GastrointestinalRecord)]
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


def lookup_gastrointestinal_record(service,repo,repository,record):
    """Read-only recovery: an uncertain write is never blindly replayed."""
    service.require_repo(repo,repository)
    if record.binding.target!=TARGET:raise UnsupportedOperation('foreign source scope')
    accounting=service.accounting();cutoff=repo.capture_cutoff()
    exact=next((row for row in service.history_rows(repo,cutoff,accounting,record.reference) if row.fact.reference==record.reference),None)
    if exact is None:return {'status':'absent'}
    if canonical_payload(exact.fact)!=canonical_payload(record):raise EvidenceConflict()
    return {'status':'committed_match','evidence':service.evidence(repo,exact,cutoff,accounting)}
