"""M5.1 transport contracts only: no clinical execution, facts or migrations."""
import ast
import asyncio
import base64
from datetime import datetime, timedelta, timezone
import importlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import event

from app.api.config import APIConfig, SyntheticScope, load_config
from app.api import dependencies as d
from app.api import errors as e
from app.api.middleware import MAX_REQUEST_BYTES, no_store
from app.api.review_commands import (ExecutionCommandCodec, InvalidCommand, InvalidStateContext,
                                    StateContext, StateContextCodec)
from app.api.schemas.common import (MAX_ENVELOPE_BYTES, CutoffView, ExactReference, QuantityView,
                                    ScopeView, TimesView)
from app.api.schemas.temporal_review import (CompletionUnknownResponse, PreparedTemporalReviewResponse,
    ReconciliationRequest, ReconciliationResponse, SelectionPin, TemporalExecutionResponse,
    TemporalReviewPreparationRequest, TemporalReviewRequest)
from app.execution.patient_state import PatientStateScope
from app.execution.patient_state_execution import (GRANT_ACTOR, GRANT_TARGET,
                                                 PatientStateTemporalExecutionRequest)
from app.execution.patient_state_inference import PatientStateTemporalRelationRequest, PatientStateSelectionPin
from app.models.clinical.common import Reference
from app.persistence.database import create_database
from app.persistence.errors import (PersistenceInputError, QueryLimitExceeded, RecordConflict,
    RecordNotFound, SchemaMismatch, ScopeMismatch, StorageIntegrityError, TransactionAborted,
    TransactionCompletionUnknown, UnsupportedOperation)
from app.persistence.mapping import canonical_payload
from app.persistence.metadata import RepositoryCutoff
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]
KEY = SecretStr('a9' * 32)
AT = datetime(2026, 10, 8, 12, tzinfo=timezone(timedelta(hours=5, minutes=30)))
EXECUTION_ID = UUID('10000000-0000-4000-8000-000000000001')


@pytest.fixture
def config(tmp_path):
    return APIConfig(database_path=tmp_path / 'never-created.sqlite', environment='test', envelope_signing_key=KEY)


@pytest.fixture
def command_request():
    # Construct the immutable request directly. No builder/governance/workflow calls.
    cutoff = RepositoryCutoff(repository_id=UUID('00000000-0000-4000-8000-000000000001'), fact_watermark=3, captured_at=AT)
    scope = PatientStateScope(patient_id='synthetic-p1', encounter_id='synthetic-e1', review_start=AT,
                              review_end=AT + timedelta(hours=2), repository_cutoff=cutoff)
    pins = [PatientStateSelectionPin(reference=Reference(kind=kind, id=name, version='1'), expected_digest=letter * 64)
            for kind, name, letter in [('observation', 'A', 'a'), ('observation', 'B', 'b'), ('medication_order', 'M', 'c')]]
    inference = PatientStateTemporalRelationRequest(scope=scope, earlier_laboratory=pins[0], later_laboratory=pins[1],
        medication=pins[2], inference_id='I', executed_at=AT + timedelta(hours=3))
    return PatientStateTemporalExecutionRequest(execution_id=EXECUTION_ID, target=GRANT_TARGET, actor=GRANT_ACTOR,
        inference_request=inference, inference_cutoff=cutoff.model_copy(update={'fact_watermark':4}),
        expected_inference_digest='d' * 64, requested_at=AT + timedelta(hours=4))


def replace(model, **updates):
    return type(model).model_validate({**model.model_dump(), **updates})


def client_app(config):
    app = create_app(config)
    return app, TestClient(app, raise_server_exceptions=False)


def test_factory_existing_routes_and_health(config):
    app, client = client_app(config)
    assert not config.database_path.exists()
    with client:
        assert client.get('/').json() == {'application':'ClinRx AI','version':'0.0.1','status':'running'}
        assert client.get('/health').json() == {'status':'ok','service':'clinrx-api'}
        assert client.get('/knowledge').status_code == 200
        assert client.get('/knowledge/NUT-STATE-001').status_code == 200
        assert client.get('/knowledge/search', params={'q':'Metabolic'}).json()[0]['knowledge_id'] == 'NUT-STATE-002'
        assert client.get('/knowledge/missing').status_code == 404
        paths = client.get('/openapi.json').json()['paths']
        assert set(paths) == {'/','/health','/knowledge','/knowledge/search','/knowledge/{knowledge_id}'}
        for path in ('/', '/health', '/knowledge'):
            assert 'cache-control' not in client.get(path).headers
    assert not config.database_path.exists()
    assert not hasattr(app.state, 'dependencies')


def test_engine_lifecycle_no_connections_and_injected_ownership(config, monkeypatch):
    import app.main as main
    actual = main.create_database
    engines, disposed = [], []
    def factory(path):
        engine = actual(path); engines.append(engine)
        event.listen(engine, 'connect', lambda *a: pytest.fail('health opened a connection'))
        event.listen(engine, 'engine_disposed', lambda *a: disposed.append(True))
        return engine
    monkeypatch.setattr(main, 'create_database', factory)
    with TestClient(create_app(config)) as client:
        client.get('/health')
    assert len(engines) == 1 and disposed == [True]
    with TestClient(create_app(config, engine=engines[0])) as client:
        client.get('/health')
    assert disposed == [True] and not config.database_path.exists()


def test_import_without_config_performs_no_io(tmp_path):
    script = "from app.main import app; print(sorted(app.openapi()['paths']))"
    env = {k:v for k,v in os.environ.items() if not k.startswith('CLINRX_')}
    env.update(PYTHONPATH=str(ROOT/'backend'), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-c', script], cwd=tmp_path, env=env, text=True, capture_output=True)
    assert result.returncode == 0 and '/health' in result.stdout
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('environment', ['local_synthetic_demo','test'])
def test_configuration_modes(config, environment):
    assert replace(config, environment=environment).environment == environment
    assert KEY.get_secret_value() not in repr(config)


@pytest.mark.parametrize('updates', [
    {'environment':'production'}, {'envelope_signing_key':''}, {'envelope_signing_key':'short'},
    {'envelope_signing_key':'z'*64}, {'api_port':False}, {'api_port':0}, {'api_port':65536},
    {'api_host':'0.0.0.0'}, {'database_path':'relative.sqlite'},
    {'clock_mode':'historical_simulation'}, {'simulation_at':AT},
    {'clock_mode':'historical_simulation','simulation_at':'2026-10-08T12:00:00'},
])
def test_invalid_configuration(config, updates):
    with pytest.raises(ValidationError): replace(config, **updates)


@pytest.mark.parametrize('origin', ['*', 'null', 'https://example.com', 'http://localhost/',
    'http://user:pass@localhost', 'http://localhost?secret=1', 'http://localhost#x',
    'http://localhost:bad', 'http://localhost:8000/path', ' http://localhost', 'http://LOCALHOST'])
def test_invalid_origin(config, origin):
    with pytest.raises(ValidationError): replace(config, allowed_dev_origins=(origin,))


def test_config_environment_and_bounded_failure(config, monkeypatch):
    for key in tuple(os.environ):
        if key.startswith('CLINRX_'): monkeypatch.delenv(key)
    with pytest.raises(RuntimeError, match='invalid ClinRx API configuration'): load_config()
    monkeypatch.setenv('CLINRX_DATABASE_PATH', str(config.database_path))
    monkeypatch.setenv('CLINRX_ENVIRONMENT', 'test')
    monkeypatch.setenv('CLINRX_ENVELOPE_SIGNING_KEY', KEY.get_secret_value())
    monkeypatch.setenv('CLINRX_ALLOWED_DEV_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
    assert load_config().allowed_dev_origins == ('http://localhost:5173','http://127.0.0.1:5173')
    monkeypatch.setenv('CLINRX_ENVELOPE_SIGNING_KEY', 'PRIVATE_SECRET')
    with pytest.raises(RuntimeError) as caught: load_config()
    assert 'PRIVATE_SECRET' not in str(caught.value) and caught.value.__suppress_context__


def test_clocks_and_access_are_explicit(config):
    assert d.make_clock(config)().utcoffset() == timedelta(0)
    historical = replace(config, clock_mode='historical_simulation', simulation_at=AT)
    assert d.make_clock(historical)() is historical.simulation_at
    access = d.SyntheticAccessContext(scopes=config.synthetic_scopes)
    access.require_scope('synthetic-p1','synthetic-e1')
    with pytest.raises(RecordNotFound): access.require_scope('synthetic-p2','synthetic-e1')


@pytest.mark.parametrize('part', ['state','command'])
def test_envelope_roundtrip_restart_and_no_clock(command_request, part, monkeypatch):
    value = StateContext(scope=command_request.inference_request.scope) if part == 'state' else command_request
    codec_type = StateContextCodec if part == 'state' else ExecutionCommandCodec
    codec = codec_type(KEY); token = codec.issue(value)
    monkeypatch.setattr(d, 'real_clock', lambda: pytest.fail('verification sampled time'))
    decoded = codec.verify(token)
    assert canonical_payload(decoded) == canonical_payload(value)
    assert codec.issue(decoded) == token
    script = r"""
import sys
from pydantic import SecretStr
from app.api.review_commands import StateContextCodec, ExecutionCommandCodec
from app.persistence.mapping import canonical_payload
kind, token = sys.stdin.read().split('\n', 1)
codec = StateContextCodec if kind == 'state' else ExecutionCommandCodec
print(canonical_payload(codec(SecretStr('a9'*32)).verify(token)))
"""
    result = subprocess.run([sys.executable, '-c', script], input=part+'\n'+token, text=True, capture_output=True,
        env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'PYTHONDONTWRITEBYTECODE':'1'})
    assert result.returncode == 0
    assert result.stdout.strip() == canonical_payload(value)
    if part == 'command':
        assert decoded.requested_at.isoformat() == command_request.requested_at.isoformat()
        assert decoded.inference_request.scope.repository_cutoff == command_request.inference_request.scope.repository_cutoff


@pytest.mark.parametrize('part', ['state','command'])
@pytest.mark.parametrize('attack', ['tamper','wrong_key','wrong_purpose','oversize','unicode','truncated','version','raw'])
def test_envelope_attacks(command_request, part, attack):
    value = StateContext(scope=command_request.inference_request.scope) if part == 'state' else command_request
    codec = (StateContextCodec if part == 'state' else ExecutionCommandCodec)(KEY)
    error = InvalidStateContext if part == 'state' else InvalidCommand
    token = codec.issue(value)
    if attack == 'tamper': token = token[:-5]+'X'+token[-4:]
    elif attack == 'wrong_key': codec = type(codec)(SecretStr('b8'*32))
    elif attack == 'wrong_purpose':
        other_value = command_request if part == 'state' else StateContext(scope=command_request.inference_request.scope)
        token = (ExecutionCommandCodec if part == 'state' else StateContextCodec)(KEY).issue(other_value)
    elif attack == 'oversize': token = 'a'*(MAX_ENVELOPE_BYTES+1)
    elif attack == 'unicode': token += 'é'
    elif attack == 'truncated': token = token[:-10]
    elif attack == 'version': token = token.replace('.v1.', '.v2.')
    else: token = canonical_payload(value)
    with pytest.raises(error) as caught: codec.verify(token)
    assert str(caught.value) == 'invalid envelope' and caught.value.__suppress_context__


@pytest.mark.parametrize('mutation', ['whitespace','duplicate','extra','alternate_base64'])
def test_even_signed_noncanonical_payload_rejected(command_request, mutation):
    codec = ExecutionCommandCodec(KEY)
    raw = canonical_payload(command_request)
    if mutation == 'whitespace': raw = ' '+raw
    elif mutation == 'duplicate': raw = raw.replace('"actor":', '"actor":"other","actor":', 1)
    elif mutation == 'extra': raw = raw[:-1]+',"unexpected":1}'
    encoded = base64.urlsafe_b64encode(raw.encode())
    if mutation == 'alternate_base64': encoded += b'='
    token = codec._signer.sign(codec._prefix+encoded).decode()
    with pytest.raises(InvalidCommand): codec.verify(token)


def test_envelope_oversized_domain_and_forged_copy(command_request):
    codec = ExecutionCommandCodec(KEY)
    with pytest.raises(InvalidCommand): codec.issue(replace(command_request, actor='x'*MAX_ENVELOPE_BYTES))
    with pytest.raises(InvalidCommand): codec.issue(command_request.model_copy(update={'workflow':'other'}))
    with pytest.raises(InvalidCommand): codec.issue(command_request.model_dump())


def preparation(command_request):
    ir = command_request.inference_request
    return dict(execution_id=EXECUTION_ID, state_context=StateContextCodec(KEY).issue(StateContext(scope=ir.scope)),
        **{field: {'reference':getattr(ir,field).reference.model_dump(), 'expected_digest':getattr(ir,field).expected_digest}
           for field in ('earlier_laboratory','later_laboratory','medication')})


@pytest.mark.parametrize('field', ['actor','final_cutoff','decision','authority','finalized_at','inference','runtime'])
def test_preparation_server_fields_forbidden(command_request, field):
    body = preparation(command_request); body[field] = 'PRIVATE'
    with pytest.raises(ValidationError): TemporalReviewPreparationRequest.model_validate(body)


def test_preparation_uuid_refs_and_deep_immutability(command_request):
    body = preparation(command_request); result = TemporalReviewPreparationRequest.model_validate(body)
    assert result.execution_id == EXECUTION_ID
    body['earlier_laboratory']['reference']['version'] = 'changed'
    assert result.earlier_laboratory.reference.version == '1'
    with pytest.raises(ValidationError): result.earlier_laboratory.reference.version = 'changed'
    with pytest.raises(ValidationError): TemporalReviewPreparationRequest.model_validate({**body,'execution_id':'bad'})
    with pytest.raises(ValidationError): ExactReference(kind='observation',id='A',version=1)
    with pytest.raises(ValidationError): TemporalReviewRequest(command='x',actor='other')
    with pytest.raises(ValidationError): ReconciliationRequest(command='x',execution_id=EXECUTION_ID)


@pytest.mark.parametrize('value', ['1.2300','-0.00','0','1.2300E+4','+.50'])
def test_decimal_strings_exact(value):
    q = QuantityView(value=value,unit_raw='mg/dL',unit_status='assessed')
    assert q.model_dump(mode='json')['value'] == value


@pytest.mark.parametrize('value', [1.23, 1, True, 'NaN','Infinity','1,2',' 1.20', 'x'*129])
def test_invalid_decimal_transport(value):
    with pytest.raises(ValidationError): QuantityView(value=value,unit_raw='mg/dL',unit_status='assessed')


@pytest.mark.parametrize('value', ['2026-10-08T12:00:00', 1234567890, None])
def test_naive_or_numeric_required_timestamp(value):
    with pytest.raises(ValidationError): CutoffView(repository_id=uuid4(),fact_watermark=1,captured_at=value)


def test_timestamp_offsets_preserved():
    value = '2026-10-08T12:00:00.123456+05:30'
    view = CutoffView(repository_id=uuid4(),fact_watermark=1,captured_at=value)
    assert view.model_dump(mode='json')['captured_at'] == value
    with pytest.raises(Exception):
        CutoffView(repository_id=uuid4(),fact_watermark=1,captured_at=datetime(2026,1,1,tzinfo=timezone(timedelta(seconds=1))))


@pytest.mark.parametrize('model', [TemporalReviewRequest,ReconciliationRequest])
def test_token_field_size_and_repr(model):
    token = 'PRIVATE_ENVELOPE'
    assert token not in repr(model(command=token))
    with pytest.raises(ValidationError): model(command='x'*(MAX_ENVELOPE_BYTES+1))


def execution_view(outcome):
    ref = dict(kind='observation',id='A',version='1')
    cutoff = dict(repository_id=str(uuid4()),fact_watermark=4,captured_at=AT.isoformat())
    evidence = dict(reference=ref,selection_digest='a'*64,time={'event':AT.isoformat(),'precision':'instant'},
        source={'namespace':'synthetic','identifier':'A','channel':'measurement'},origin='observed',verification='verified',
        conflict='none_known',temporal_status='historical',provenance_recorded_at=AT.isoformat(),
        provenance_completeness='complete',ingested_at=AT.isoformat(),disclosures=[])
    lab = {**evidence,'concept_id':'synthetic-serum-creatinine','quantity':{'value':'1.00','unit_raw':'mg/dL','unit_status':'assessed'}}
    med = {**evidence,'event_type':'medication_order','status':'active','product_id':'synthetic-drug'}
    inference = dict(reference={**ref,'kind':'inference','id':'I'},method={**ref,'kind':'inference_method'},
        statement=None if outcome=='withheld' else 'Synthetic descriptive statement.',applicability='Synthetic only',
        uncertainty=['unknown completeness'],limitations=['No causality'],inputs=[ref,ref,ref])
    return TemporalExecutionResponse(execution_id=EXECUTION_ID,finalized_at=AT,ingested_at=AT,
        context={'reference':{**ref,'kind':'snapshot'},'evidence_references':[ref]*4,'limitations':['partial']},
        governance={'outcome':outcome,'decision_reference':{**ref,'kind':'decision'},'decided_at':AT,
            'reasons':[],'safety_status':'assessed','fidelity_status':'matched','freshness_status':'assessed',
            'authority_status':'assessed','limitations':['synthetic']},
        provenance={'inference':inference,'earlier_laboratory':lab,'later_laboratory':lab,'medication':med,
            'terminal_references':[ref]*3,'inference_terminal_reference':inference['reference'],
            'direct_dependencies':[{'target':ref}]*3,'input_cutoff':cutoff,'inference_cutoff':cutoff,
            'final_cutoff':cutoff,'final_recheck':'unchanged','recheck_reasons':[]})


@pytest.mark.parametrize('outcome', ['released','withheld'])
def test_completed_outcomes_are_success_contracts(outcome):
    execution = execution_view(outcome)
    result = ReconciliationResponse(status='committed_match',execution=execution)
    assert result.execution.governance.outcome == outcome
    assert result.execution.provenance.earlier_laboratory.quantity.value == '1.00'
    with pytest.raises(ValidationError): result.execution.governance.outcome = 'released'
    with pytest.raises(ValidationError): ReconciliationResponse(status='absent',execution=execution)
    assert ReconciliationResponse(status='absent',execution=None).execution is None


@pytest.mark.parametrize('error,status,code', [
    (RecordNotFound,404,'not_found'), (ScopeMismatch,404,'not_found'), (RecordConflict,409,'execution_conflict'),
    (StorageIntegrityError,500,'storage_integrity_failure'), (SchemaMismatch,503,'storage_unavailable'),
    (TransactionAborted,503,'transaction_failed'), (TransactionCompletionUnknown,503,'completion_unknown'),
    (InvalidCommand,422,'invalid_command'), (InvalidStateContext,422,'invalid_state_context'),
    (PersistenceInputError,422,'invalid_request'), (UnsupportedOperation,422,'unsupported_review_input'),
    (QueryLimitExceeded,422,'bounded_view_limit_exceeded'), (e.RequestTooLarge,413,'request_too_large'),
    (RuntimeError,500,'internal_error')])
def test_bounded_error_mapping(config, error, status, code):
    app, client = client_app(config)
    @app.get('/test-error')
    def route(): raise error('PRIVATE SELECT * FROM /secret patient payload')
    with client:
        response = client.get('/test-error')
    assert response.status_code == status and response.json()['code'] == code
    assert 'PRIVATE' not in response.text and 'SELECT' not in response.text and '/secret' not in response.text


def test_completion_unknown_has_explicit_execution_identity(config):
    from fastapi import Request
    app, client = client_app(config)
    @app.get('/test-uncertain')
    def route(request: Request):
        request.state.execution_id = EXECUTION_ID
        raise TransactionCompletionUnknown('PRIVATE')
    with client: response = client.get('/test-uncertain')
    assert response.status_code == 503
    assert response.json() == {'status':'completion_unknown','execution_id':str(EXECUTION_ID),
        'next_action':'reconcile','automatic_retry':False,'correlation_id':response.headers['x-correlation-id']}


def test_validation_privacy_and_logging(config, caplog):
    app, client = client_app(config)
    @app.post('/test/{patient_id}', dependencies=[Depends(no_store)])
    def route(patient_id: str, body: TemporalReviewPreparationRequest): return {'ok':True}
    secret = 'PRIVATE_CLINICAL_VALUE'
    with caplog.at_level(logging.INFO, logger='clinrx.api'), client:
        response = client.post('/test/PRIVATE_PATIENT',json={'execution_id':secret,secret:'SELECT PRIVATE',
            'command':secret,'state_context':secret}, headers={'X-Correlation-ID':secret})
    assert response.status_code == 422 and response.headers['cache-control'] == 'no-store'
    assert secret not in response.text and 'SELECT' not in response.text
    records = [x for x in caplog.records if x.name == 'clinrx.api']
    assert len(records) == 1 and records[0].route_template == '/test/{patient_id}'
    assert 'PRIVATE' not in str(records[0].__dict__) and 'SELECT' not in str(records[0].__dict__)
    UUID(response.headers['x-correlation-id'])
    for field in response.json()['fields']:
        assert set(field) == {'path','code'}


def test_dependencies_injectable_and_actor_not_from_headers(config):
    app, client = client_app(config)
    marker = object()
    app.dependency_overrides[d.get_engine] = lambda: marker
    app.dependency_overrides[d.get_workflow_clock] = lambda: lambda: AT
    app.dependency_overrides[d.get_state_context_codec] = lambda: 'injected'
    app.dependency_overrides[d.get_execution_command_codec] = lambda: 'command-codec'
    app.dependency_overrides[d.get_access_context] = lambda: d.SyntheticAccessContext(scopes=())
    @app.get('/test-dependencies')
    def route(engine=Depends(d.get_engine),clock=Depends(d.get_workflow_clock),identity=Depends(d.get_synthetic_identity),
              signer=Depends(d.get_state_context_codec),command=Depends(d.get_execution_command_codec),
              access=Depends(d.get_access_context),settings=Depends(d.get_config)):
        assert engine is marker and clock() == AT and signer == 'injected' and command == 'command-codec'
        assert access.scopes == () and settings == config
        return {'actor':identity.actor,'target_request_id':identity.target.request_id}
    with client: response = client.get('/test-dependencies',headers={'X-Actor':'PRIVATE'})
    assert response.json()['actor'] == GRANT_ACTOR
    assert response.json()['target_request_id'] == GRANT_TARGET.request_id != response.headers['x-correlation-id']


def test_cors_exact_origins(config):
    config = replace(config,allowed_dev_origins=('http://localhost:5173',))
    with TestClient(create_app(config)) as client:
        allowed = client.options('/health',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'GET'})
        denied = client.options('/health',headers={'Origin':'http://evil.test','Access-Control-Request-Method':'GET'})
    assert allowed.status_code == 200 and allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert 'access-control-allow-credentials' not in allowed.headers and denied.status_code == 400


def test_declared_and_streamed_body_limits(config):
    app, client = client_app(config)
    @app.post('/test-size')
    def route(body: TemporalReviewRequest): return {'ok':True}
    with client:
        for content in ('x'*(MAX_REQUEST_BYTES+1), iter([b'x'*100000]*3)):
            response = client.post('/test-size',content=content)
            assert response.status_code == 413 and response.json()['code'] == 'request_too_large'


def test_launcher_disables_raw_path_access_log(config, monkeypatch):
    from app.api import run
    called = []
    monkeypatch.setattr(run, 'load_config', lambda: config)
    monkeypatch.setattr(run.uvicorn, 'run', lambda *a,**kw: called.append(kw))
    run.main()
    assert called == [{'host':'127.0.0.1','port':8000,'access_log':False}]


def test_no_clinical_calls_or_orm_in_new_api_code():
    prohibited = {'execute_patient_state_temporal_review','reconcile_patient_state_temporal_execution',
        'build_patient_state_temporal_inference','assemble_patient_state','assess_release','decide_release',
        'append_fact','append_revision','select','Session','create_all'}
    for path in (ROOT/'backend/app/api').rglob('*.py'):
        tree = ast.parse(path.read_text())
        calls = {n.func.id if isinstance(n.func,ast.Name) else n.func.attr for n in ast.walk(tree)
                 if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
        assert not calls.intersection(prohibited), path
        assert 'app.persistence.entities' not in path.read_text()


def test_transport_window_microsecond_order_without_float_loss():
    start = datetime(9999,1,1,0,0,0,1,tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        ScopeView(patient_id='synthetic-p1', encounter_id='synthetic-e1', review_start=start,
            review_end=start-timedelta(microseconds=1), repository_cutoff={
                'repository_id':uuid4(),'fact_watermark':1,'captured_at':start})


def test_transport_dst_and_offset_equal_instants_preserved():
    from zoneinfo import ZoneInfo
    early = datetime(2026,11,1,1,30,tzinfo=ZoneInfo('America/New_York'),fold=0)
    late = early.replace(fold=1)
    cutoff = {'repository_id':uuid4(),'fact_watermark':1,'captured_at':early}
    view = ScopeView(patient_id='synthetic-p1',encounter_id='synthetic-e1',review_start=early,
                     review_end=late,repository_cutoff=cutoff)
    assert view.model_dump(mode='json')['review_start'].endswith('-04:00')
    assert view.model_dump(mode='json')['review_end'].endswith('-05:00')
    with pytest.raises(ValidationError):
        ScopeView(patient_id='synthetic-p1',encounter_id='synthetic-e1',review_start=late,
                  review_end=early,repository_cutoff=cutoff)
    equal = replace(view, review_end=early.astimezone(timezone.utc))
    assert equal.review_end == early.astimezone(timezone.utc)


def test_envelope_operations_do_not_access_storage_or_clinical_producers(command_request, monkeypatch):
    from app.execution import patient_state_inference, patient_state_workflow
    from app.persistence import repository
    def forbidden(*a, **k): pytest.fail('transport invoked clinical work')
    monkeypatch.setattr(patient_state_inference, 'build_patient_state_temporal_inference', forbidden)
    monkeypatch.setattr(patient_state_workflow, 'execute_patient_state_temporal_review', forbidden)
    monkeypatch.setattr(patient_state_workflow, 'reconcile_patient_state_temporal_execution', forbidden)
    monkeypatch.setattr(repository, 'transaction', forbidden)
    codec = ExecutionCommandCodec(KEY)
    assert canonical_payload(codec.verify(codec.issue(command_request))) == canonical_payload(command_request)


@pytest.mark.parametrize('year', [1, 2026, 9999])
@pytest.mark.parametrize('delta', [timedelta(seconds=1), timedelta(microseconds=1)])
def test_window_reversals_across_supported_date_range(year, delta):
    start = datetime(year, 6, 1, 12, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        ScopeView(patient_id='synthetic-p1', encounter_id='synthetic-e1', review_start=start,
            review_end=start-delta, repository_cutoff={
                'repository_id':uuid4(), 'fact_watermark':1, 'captured_at':start})


@pytest.mark.parametrize('year', [1, 2026, 9999])
def test_window_exact_equality(year):
    at = datetime(year, 6, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
    view = ScopeView(patient_id='synthetic-p1', encounter_id='synthetic-e1', review_start=at,
        review_end=at, repository_cutoff={'repository_id':uuid4(),'fact_watermark':1,'captured_at':at})
    assert view.review_start.isoformat() == view.review_end.isoformat() == at.isoformat()


@pytest.mark.parametrize('field', ['review_start', 'review_end'])
def test_window_rejects_naive_boundary(field):
    values = dict(patient_id='synthetic-p1', encounter_id='synthetic-e1', review_start=AT,
        review_end=AT, repository_cutoff={'repository_id':uuid4(),'fact_watermark':1,'captured_at':AT})
    values[field] = AT.replace(tzinfo=None)
    with pytest.raises(ValidationError): ScopeView(**values)


@pytest.mark.parametrize('value', ['1760000000', '1760000000.123456',
    '2026-10-08T12:00:00.1234567+05:30', '2026-10-08T12:00:00.0000001Z'])
def test_timestamp_lexical_coercion_and_precision_loss_rejected(value):
    with pytest.raises(ValidationError):
        CutoffView(repository_id=uuid4(), fact_watermark=1, captured_at=value)


def test_oversized_content_length_numeral_is_bounded_413(config):
    with TestClient(create_app(config), raise_server_exceptions=False) as client:
        response = client.get('/health', headers={'content-length':'9'*5000})
    assert response.status_code == 413 and response.json()['code'] == 'request_too_large'
