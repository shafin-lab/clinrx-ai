"""Opt-in, loopback-only synthetic source-record authoring. Not a production route."""
import os
import secrets
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import model_validator
from starlette.responses import JSONResponse
from app.api.dependencies import get_engine
from app.api.schemas.common import DTO, Digest
from app.models.clinical.common import ContextTarget
from app.models.clinical.hemodynamics import CirculatoryRecord
from app.persistence.canonical import canonical_payload
from app.persistence.errors import RecordConflict, RecordNotFound, TransactionCompletionUnknown
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction
from app.demo.hosting import SyntheticDemoGateway, PREFIX

TARGET = ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e1')
ENTRY = PREFIX + '/synthetic-evidence'

class EvidenceConflict(Exception):
    pass

async def evidence_conflict(request, error):
    return JSONResponse({'code': 'evidence_conflict', 'message': 'The exact evidence revision conflicts or the repository changed.'}, status_code=409, headers={'Cache-Control': 'no-store'})

class EvidenceDraft(DTO):
    repository_id: UUID
    fact: CirculatoryRecord
    predecessor_digest: Digest | None = None

    @model_validator(mode='after')
    def correspondence(self):
        if self.fact.binding.target != TARGET:
            raise ValueError('synthetic encounter required')
        if (self.fact.supersedes is None) != (self.predecessor_digest is None):
            raise ValueError('correction requires exact predecessor digest')
        if self.fact.supersedes and (self.fact.supersedes.kind != self.fact.kind or self.fact.supersedes.id != self.fact.id):
            raise ValueError('correction must retain source identity')
        return self


def require_repository(repository, body):
    if repository.capture_cutoff().repository_id != body.repository_id:
        raise EvidenceConflict()


def view(body, stored=None):
    fact = stored.fact if stored else body.fact
    return {'repository_id': str(body.repository_id), 'fact': fact.model_dump(mode='json'),
            'expected_digest': fact.canonical_digest, 'canonical_fact': canonical_payload(fact),
            'ingestion': stored.ingestion.model_dump(mode='json') if stored else None}


def write_evidence(engine, body):
    # Both predecessor comparison and append share BEGIN IMMEDIATE. The existing
    # repository handles exact retries before terminal checks, never overwrites.
    with execution_transaction(engine) as tx:
        repository = tx.repository
        require_repository(repository, body)
        if body.fact.supersedes:
            predecessor = repository.load_fact(body.fact.supersedes, target=TARGET)
            if predecessor.fact.canonical_digest != body.predecessor_digest:
                raise EvidenceConflict()
        stored = (repository.append_revision(body.fact, target=TARGET) if body.fact.supersedes
                  else repository.append_fact(body.fact, target=TARGET))
        result = view(body, stored)
    return result


router = APIRouter()

@router.post(ENTRY + '/validate')
def validate_draft(body: EvidenceDraft, engine=Depends(get_engine)):
    with transaction(engine) as repository:
        require_repository(repository, body)
    return view(body)

@router.post(ENTRY)
def save(body: EvidenceDraft, engine=Depends(get_engine)):
    try:
        return write_evidence(engine, body)
    except RecordConflict:
        raise EvidenceConflict() from None
    except RecordNotFound:
        raise EvidenceConflict() from None
    except TransactionCompletionUnknown:
        return JSONResponse({'code': 'evidence_completion_unknown'}, status_code=503)

@router.post(ENTRY + '/lookup')
def lookup(body: EvidenceDraft, engine=Depends(get_engine)):
    # Read-only exact lookup. Absence never triggers append or replacement.
    try:
        with transaction(engine) as repository:
            require_repository(repository, body)
            stored = repository.load_fact(body.fact.reference, target=TARGET)
            if canonical_payload(stored.fact) != canonical_payload(body.fact):
                raise EvidenceConflict()
            result = view(body, stored)
    except RecordNotFound:
        return {'status': 'absent'}
    return {'status': 'committed_match', 'evidence': result}


class SyntheticAuthoringGateway(SyntheticDemoGateway):
    """Separate entry point. Existing read-only gateway and Docker image unchanged."""
    def __init__(self, database: Path, frontend: Path, signing_key: str, origin: str):
        from urllib.parse import urlsplit
        parsed = urlsplit(origin)
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('explicit IPv4 loopback origin required')
        self.origin = origin
        self.host = parsed.netloc
        super().__init__(database, frontend, signing_key)
        self.core.include_router(router)
        self.core.add_exception_handler(EvidenceConflict, evidence_conflict)

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            if not scope.get('client') or scope['client'][0] not in ('127.0.0.1', '::1'):
                return await JSONResponse({'code': 'loopback_only'}, status_code=403)(scope, receive, send)
            headers = dict(scope.get('headers', ()))
            if headers.get(b'host', b'').decode() != self.host:
                return await JSONResponse({'code': 'invalid_local_host'}, status_code=403)(scope, receive, send)
            if scope['path'] == '/health' and scope['method'] == 'GET':
                return await JSONResponse({'status': 'ok', 'mode': 'synthetic-evidence-authoring', 'execution_enabled': False}, headers={'Cache-Control': 'no-store'})(scope, receive, send)
            if scope['path'] in (ENTRY, ENTRY + '/validate', ENTRY + '/lookup'):
                if (scope['method'] != 'POST' or headers.get(b'origin', b'').decode() != self.origin
                    or headers.get(b'sec-fetch-site', b'same-origin') not in (b'same-origin', b'none')
                    or headers.get(b'content-type', b'').split(b';')[0] != b'application/json'):
                    return await JSONResponse({'code': 'local_authoring_denied'}, status_code=403,
                        headers={'Cache-Control': 'no-store'})(scope, receive, send)
                async def no_store(message):
                    if message['type'] == 'http.response.start':
                        message = {**message, 'headers': [*message.get('headers', ()), (b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff')]}
                    await send(message)
                return await self.core(scope, receive, no_store)
        return await super().__call__(scope, receive, send)


def from_environment():
    return SyntheticAuthoringGateway(Path(os.environ['CLINRX_AUTHORING_DATABASE']),
        Path(os.environ['CLINRX_AUTHORING_FRONTEND']), secrets.token_hex(32),
        os.environ['CLINRX_AUTHORING_ORIGIN'])
