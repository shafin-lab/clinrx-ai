"""Shared exact-identity admission for RF2 narrative source records."""
from hashlib import sha256

from app.demo.authoring import TARGET, EvidenceConflict
from app.persistence.canonical import canonical_payload
from app.persistence.errors import UnsupportedOperation


def require_source_identity(record, record_type, owner_prefix, label):
    if not isinstance(record, record_type) or record.binding.target != TARGET or record.origin not in ('observed', 'reported'):
        raise UnsupportedOperation(f'{label} record must be a typed observed or reported record in this synthetic encounter')
    identity = record.source_identity
    source_key = (identity.issuer_namespace + '\0' + identity.source_report_id).encode()
    owner = owner_prefix + sha256(source_key).hexdigest()[:32]
    if record.id != owner or record.revision != identity.source_version:
        raise UnsupportedOperation(f'{label} owner and revision must preserve exact source identity/version')


def _exact_match(rows, record):
    exact = next((row for row in rows if row.fact.reference == record.reference), None)
    if exact is not None and canonical_payload(exact.fact) != canonical_payload(record):
        raise EvidenceConflict()
    return exact


def append_recorded_source(service, repo, record):
    accounting = service.accounting()
    cutoff = repo.capture_cutoff()
    rows = service.history_rows(repo, cutoff, accounting, record.reference)
    exact = _exact_match(rows, record)
    if exact is not None:
        return service.evidence(repo, exact, cutoff, accounting)

    # Exact linked sources are loaded in the same encounter before any append.
    for reference in record.linked_sources:
        repo.load_fact(reference, target=TARGET)
    if not rows:
        if record.supersedes is not None or record.change_state != 'original':
            raise EvidenceConflict()
        stored = repo.append_fact(record, target=TARGET)
    else:
        terminal = rows[-1].fact
        if (record.supersedes != terminal.reference or record.change_state == 'original'
                or record.category != terminal.category
                or record.source_identity.accession_id != terminal.source_identity.accession_id
                or record.source_identity.issuer_namespace != terminal.source_identity.issuer_namespace
                or record.source_identity.source_report_id != terminal.source_identity.source_report_id):
            raise EvidenceConflict()
        stored = repo.append_revision(record, target=TARGET)
    return service.evidence(repo, stored, repo.capture_cutoff(), accounting)


def lookup_recorded_source(service, repo, record):
    """Read the exact committed payload without retrying a write."""
    accounting = service.accounting()
    cutoff = repo.capture_cutoff()
    exact = _exact_match(service.history_rows(repo, cutoff, accounting, record.reference), record)
    if exact is None:
        return {'status': 'absent'}
    return {'status': 'committed_match', 'evidence': service.evidence(repo, exact, cutoff, accounting)}
