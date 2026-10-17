"""M1 pure synthetic state contracts: no repository fixtures or clinical reasoning."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.execution import patient_state as state
from app.models.clinical.common import (
    Binding, ClinicalTime, ClinicalValue, ContextTarget, IdentityVerification,
    LineageEdge, Provenance, Quantity, Reference, Source, Unit,
)
from app.models.clinical.facts import Dose, Frequency, MedicationIdentity
from app.persistence.errors import UnsupportedOperation
from app.persistence.mapping import canonical_payload
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff

AT = datetime(2026, 10, 8, 8, 0, 0, 123456, tzinfo=timezone(timedelta(hours=5, minutes=30)))
REPOSITORY = UUID('00000000-0000-4000-8000-000000000001')
SOURCE = Source(namespace='synthetic.source', identifier='record-source', version='raw-v1', channel='external_record')
TARGET = ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e1')
DOMAINS = ('laboratory', 'medication', 'antimicrobial', 'hemodynamic_support', 'respiratory_support',
           'renal_support', 'fluid_output', 'microbiology', 'procedure', 'history_event')


def replace(model, **changes):
    return type(model).model_validate({**model.model_dump(), **changes})


def quantity(value='1.2300', unit=' raw-unit '):
    return Quantity(value=Decimal(value), unit=Unit(raw=unit, status='unresolved', limitation='retained source spelling'))


def value(number='1.2300'):
    return ClinicalValue(status='known', value=quantity(number))


def scope(**changes):
    return state.PatientStateScope(patient_id=TARGET.patient_id, encounter_id=TARGET.encounter_id,
        review_start=AT, review_end=AT+timedelta(hours=6), repository_cutoff=RepositoryCutoff(
            repository_id=REPOSITORY, fact_watermark=100, captured_at=AT+timedelta(days=1)), **changes)


def payload(domain):
    drug = MedicationIdentity(ingredient_ids=('recorded-ingredient',), product_id='source-product', formulation='source formulation')
    frequency = Frequency(occurrences=2, interval=quantity('24.00', 'hours'))
    dose = Dose(amount=quantity('2.500', 'mg'), basis='per_dose', frequency=frequency)
    parameter = state.RecordedParameter(concept_id='recorded-setting', value=value('10.00'))
    specimen = Source(namespace='synthetic.specimen', identifier='sample-1', channel='external_record')
    return {
        'laboratory': state.LaboratoryState(concept_id='source-laboratory-code', value=value(), specimen=specimen, status='final'),
        'medication': state.MedicationState(medication=drug, dose=dose, frequency=frequency, route='source route', status='changed'),
        'antimicrobial': state.AntimicrobialState(medication=drug, dose=dose, frequency=frequency, route='source route', status='administered', recorded_indication='recorded context'),
        'hemodynamic_support': state.HemodynamicSupportState(support_id='source-support', agent=drug, status='active', rate=quantity('0.050'), parameters=(parameter,)),
        'respiratory_support': state.RespiratorySupportState(mode='source respiratory mode', status='active', parameters=(parameter,)),
        'renal_support': state.RenalSupportState(modality='source renal modality', status='inactive', parameters=(parameter,)),
        'fluid_output': state.FluidOutputState(category='recorded balance', quantity=quantity('-12.00', 'mL'), site='recorded site'),
        'microbiology': state.MicrobiologyState(specimen=specimen, specimen_type='source specimen type', collected_at=AT-timedelta(hours=1),
            organisms=('organism-source-code',), result=ClinicalValue(status='known', value='source result'), status='preliminary',
            susceptibilities=(state.RecordedSusceptibility(antimicrobial=drug, result=value('0.500'), method='source method'),)),
        'procedure': state.ProcedureState(concept_id='source-procedure-code', status='performed', site='source site'),
        'history_event': state.HistoryEventState(concept_id='source-event-code', status='reported', recorded_context='explicit prior record'),
    }[domain]


def item(domain='laboratory', *, index=1, at=AT, **changes):
    p = payload(domain)
    kind = 'medication_order' if domain in ('medication', 'antimicrobial') else 'procedure' if domain == 'procedure' else 'condition' if domain == 'history_event' else 'observation'
    data = dict(reference=Reference(kind=kind, id=f'fact-{index}', version='rev-A'),
        binding=Binding(target=TARGET, verification=IdentityVerification(status='unresolved', method='source assertion', verifier='synthetic',
            assessed_at=AT, source=SOURCE, ambiguity='not authenticated')),
        origin='reported', time=ClinicalTime(event=at, recorded=at+timedelta(minutes=5), retrieved=at+timedelta(minutes=10),
            processed=at+timedelta(minutes=15), precision='instant'),
        provenance=Provenance(source=SOURCE, actor='source-author', recorded_at=at+timedelta(minutes=5),
            lineage='unknown', limitations=('source evidence only',)),
        ingestion=IngestionMetadata(repository_id=REPOSITORY, ingestion_sequence=index, ingested_at=AT+timedelta(days=1)),
        payload=p, payload_digest=sha256(canonical_payload(p).encode()).hexdigest(), disclosures=('synthetic evidence',))
    data.update(changes)
    return state.RetainedStateItem(**data)


def snapshot(**buckets):
    return state.PatientStateSnapshot(scope=scope(), **buckets)


def full_snapshot():
    return snapshot(**{domain:(item(domain, index=i+1, at=AT+timedelta(minutes=i*20)),) for i, domain in enumerate(DOMAINS)})


def test_scope_and_empty_snapshot():
    s = scope()
    assert s.target == TARGET and s.state_contract_version == '1'
    assert s.review_start.isoformat() == '2026-10-08T08:00:00.123456+05:30'
    assert s.repository_cutoff.repository_id == REPOSITORY
    assert state.PatientStateSnapshot(scope=s).ordered_items == ()
    assert replace(s, review_end=AT).review_end == AT


@pytest.mark.parametrize('part', ['patient', 'encounter', 'reversed', 'naive_start', 'naive_end', 'version', 'uuid', 'watermark', 'forged_cutoff'])
def test_invalid_scope(part):
    s = scope()
    if part in ('patient', 'encounter'): updates = {part+'_id':' '}
    elif part == 'reversed': updates = {'review_end':AT-timedelta(microseconds=1)}
    elif part == 'naive_start': updates = {'review_start':AT.replace(tzinfo=None)}
    elif part == 'naive_end': updates = {'review_end':AT.replace(tzinfo=None)}
    elif part == 'version': updates = {'state_contract_version':'2'}
    else:
        cutoff = s.repository_cutoff.model_dump()
        cutoff['repository_id' if part == 'uuid' else 'fact_watermark'] = 'bad' if part == 'uuid' else True
        updates = {'repository_cutoff':s.repository_cutoff.model_copy(update={'fact_watermark':True}) if part == 'forged_cutoff' else cutoff}
    with pytest.raises(ValueError): replace(s, **updates)


@pytest.mark.parametrize('domain', DOMAINS)
def test_every_domain_roundtrip_exact_source_and_values(domain):
    original = item(domain)
    restored = state.RetainedStateItem.model_validate_json(canonical_payload(original))
    assert type(restored.payload) is type(original.payload)
    assert canonical_payload(restored) == canonical_payload(original)
    assert restored.reference == Reference(kind=original.reference.kind, id='fact-1', version='rev-A')
    assert restored.provenance.source == SOURCE
    assert restored.payload_digest == sha256(canonical_payload(original.payload).encode()).hexdigest()
    assert restored.domain == domain and restored.origin == 'reported'
    assert getattr(snapshot(**{domain:(original,)}), domain) == (original,)


def test_all_domains_independent_times_and_no_lineage_promotion():
    result = full_snapshot()
    assert tuple(i.domain for i in result.ordered_items) == DOMAINS
    assert tuple(i.time.event for i in result.ordered_items) == tuple(AT+timedelta(minutes=i*20) for i in range(10))
    assert tuple(i.ingestion.ingestion_sequence for i in result.ordered_items) == tuple(range(1,11))
    assert not hasattr(result, 'dependencies') and not hasattr(result, 'lineage')
    assert not hasattr(result, 'decision') and not hasattr(result, 'state_time')
    assert state.PatientStateSnapshot.model_validate_json(canonical_payload(result)).canonical_digest == result.canonical_digest


@pytest.mark.parametrize('domain', DOMAINS)
def test_domain_bucket_mismatch(domain):
    wrong = 'laboratory' if domain != 'laboratory' else 'medication'
    with pytest.raises(ValueError): snapshot(**{wrong:(item(domain),)})


@pytest.mark.parametrize('domain', DOMAINS)
def test_inference_reference_cannot_masquerade_as_recorded_item(domain):
    with pytest.raises(ValueError): item(domain, reference=Reference(kind='inference', id='x', version='1'))


@pytest.mark.parametrize('part', ['patient', 'encounter', 'repository', 'future_sequence', 'duplicate_sequence'])
def test_snapshot_scope_prefix_and_identity_rejection(part):
    original = item()
    if part in ('patient', 'encounter'):
        original = replace(original, binding=replace(original.binding, target=replace(TARGET, **{part+'_id':'other'})))
    elif part == 'repository': original = replace(original, ingestion=replace(original.ingestion, repository_id=UUID(int=2)))
    elif part == 'future_sequence': original = replace(original, ingestion=replace(original.ingestion, ingestion_sequence=101))
    else:
        other = replace(original, reference=Reference(kind='observation', id='other', version='1'))
        with pytest.raises(ValueError): snapshot(laboratory=(original,other))
        return
    with pytest.raises(ValueError): snapshot(laboratory=(original,))


@pytest.mark.parametrize('part', ['same', 'contradictory', 'cross_domain'])
def test_duplicate_exact_refs_rejected(part):
    original = item()
    other = replace(original, ingestion=replace(original.ingestion, ingestion_sequence=2))
    if part == 'contradictory': other = replace(other, provenance=replace(other.provenance, actor='other'))
    if part == 'cross_domain':
        other = item('fluid_output', index=2, reference=original.reference)
        with pytest.raises(ValueError): snapshot(laboratory=(original,), fluid_output=(other,))
    else:
        with pytest.raises(ValueError): snapshot(laboratory=(original,other))


def test_distinct_revisions_retained_without_terminal_selection():
    first = item()
    second = replace(first, reference=replace(first.reference, version='rev-B'), ingestion=replace(first.ingestion, ingestion_sequence=2))
    result = snapshot(laboratory=(second,first))
    assert [i.reference.version for i in result.laboratory] == ['rev-A','rev-B']


@pytest.mark.parametrize('domain', ['laboratory', 'medication', 'antimicrobial', 'hemodynamic_support', 'microbiology'])
def test_payload_type_cannot_be_relabelled(domain):
    source = payload(domain).model_dump()
    source['domain'] = 'procedure' if domain != 'laboratory' else 'medication'
    with pytest.raises(ValueError): item(domain, payload=source)


@pytest.mark.parametrize('at,valid', [(AT,True), (AT+timedelta(hours=6),True), (AT-timedelta(microseconds=1),False), (AT+timedelta(hours=6,microseconds=1),False)])
def test_closed_event_window_boundaries(at, valid):
    i = item(at=at)
    if valid: assert snapshot(laboratory=(i,)).laboratory == (i,)
    else:
        with pytest.raises(ValueError): snapshot(laboratory=(i,))


def test_prior_history_requires_explicit_contextual_basis():
    old = item('history_event', at=AT-timedelta(days=365))
    with pytest.raises(ValueError): snapshot(history_event=(old,))
    context = replace(old, temporal_basis='contextual_history')
    assert snapshot(history_event=(context,)).history_event[0].time.event == old.time.event
    with pytest.raises(ValueError): replace(item(), temporal_basis='contextual_history')
    with pytest.raises(ValueError): snapshot(history_event=(item('history_event', at=AT+timedelta(days=1), temporal_basis='contextual_history'),))


@pytest.mark.parametrize('start,end,valid', [
    (AT-timedelta(days=1),AT,True), (AT+timedelta(hours=6),AT+timedelta(days=1),True),
    (AT-timedelta(days=1),None,True), (AT-timedelta(days=2),AT-timedelta(microseconds=1),False),
    (AT+timedelta(hours=6,microseconds=1),None,False),
])
def test_interval_overlap_does_not_force_event_clock(start, end, valid):
    i = item('medication', time=ClinicalTime(effective_start=start, effective_end=end, precision='approximate', uncertainty='source interval'), temporal_basis='effective_interval')
    if valid: assert snapshot(medication=(i,)).medication[0].time.event is None
    else:
        with pytest.raises(ValueError): snapshot(medication=(i,))


@pytest.mark.parametrize('basis', ['event', 'effective_interval', 'contextual_history'])
def test_missing_clinical_time_never_falls_back_to_ingestion(basis):
    with pytest.raises(ValueError): item('history_event', temporal_basis=basis, time=ClinicalTime(precision='unknown'))


def test_time_and_source_availability_never_collapsed():
    original = item()
    t = original.time
    assert (t.event, t.recorded, t.retrieved, t.processed) == (AT,AT+timedelta(minutes=5),AT+timedelta(minutes=10),AT+timedelta(minutes=15))
    assert original.ingestion.ingested_at == AT+timedelta(days=1)
    assert original.provenance.recorded_at == AT+timedelta(minutes=5)
    # Cutoff captured_at is metadata, not an availability/event-time ceiling.
    s = replace(scope(), repository_cutoff=replace(scope().repository_cutoff, captured_at=AT-timedelta(days=10)))
    assert state.PatientStateSnapshot(scope=s, laboratory=(original,)).laboratory == (original,)


def test_deterministic_time_then_reference_order_not_ingestion_order():
    a = item(index=3, at=AT)
    b = item(index=1, at=AT+timedelta(minutes=1))
    c = item(index=2, at=AT)
    first = snapshot(laboratory=(b,a,c), disclosures=('first','second'))
    second = snapshot(laboratory=(c,b,a), disclosures=('first','second'))
    assert [i.reference.id for i in first.laboratory] == ['fact-2','fact-3','fact-1']
    assert canonical_payload(first) == canonical_payload(second)
    assert first.disclosures == ('first','second')
    assert first.canonical_digest == sha256(canonical_payload(first).encode()).hexdigest()


def test_equal_instants_order_by_domain_then_exact_reference():
    a = item('laboratory', index=1)
    b = item('fluid_output', index=2, at=AT.astimezone(timezone.utc))
    result = snapshot(laboratory=(a,), fluid_output=(b,))
    assert [i.domain for i in result.ordered_items] == ['fluid_output','laboratory']
    assert result.ordered_items[0].time.event.isoformat().endswith('+00:00')
    assert result.ordered_items[1].time.event.isoformat().endswith('+05:30')


def test_dst_fold_order_by_actual_instant():
    zone = ZoneInfo('America/New_York')
    early = datetime(2026,11,1,1,30,tzinfo=zone,fold=0)
    late = datetime(2026,11,1,1,15,tzinfo=zone,fold=1)
    s = replace(scope(), review_start=early, review_end=late)
    a,b = item(index=2,at=early),item(index=1,at=late)
    result = state.PatientStateSnapshot(scope=s,laboratory=(b,a))
    assert [i.reference.id for i in result.laboratory] == ['fact-2','fact-1']
    assert state.PatientStateSnapshot.model_validate_json(canonical_payload(result)).canonical_digest == result.canonical_digest
    with pytest.raises(ValueError): replace(s,review_start=late,review_end=early)


@pytest.mark.parametrize('part', ['payload', 'source', 'time', 'ingestion'])
def test_item_digest_detects_representation_changes(part):
    a = item()
    if part == 'payload':
        p = replace(a.payload, value=value('1.23000'))
        b = replace(a, payload=p, payload_digest=sha256(canonical_payload(p).encode()).hexdigest())
        assert p.value.value.value == a.payload.value.value.value and b.payload_digest != a.payload_digest
    elif part == 'source': b = replace(a, provenance=replace(a.provenance, source=replace(SOURCE, identifier='other')))
    elif part == 'time': b = replace(a, time=replace(a.time,event=AT.astimezone(timezone.utc)))
    else: b = replace(a, ingestion=replace(a.ingestion,ingested_at=AT+timedelta(days=2)))
    assert a.canonical_digest != b.canonical_digest


@pytest.mark.parametrize('bad', ['0'*64, 'bad', 'A'*64])
def test_invalid_payload_digest(bad):
    with pytest.raises(ValueError): item(payload_digest=bad)


@pytest.mark.parametrize('part', ['item', 'payload', 'quantity', 'unit', 'source', 'time', 'scope', 'snapshot', 'metadata', 'parameter'])
def test_deep_frozen_models(part):
    i = item('hemodynamic_support')
    objects = {'item':(i,'origin','observed'), 'payload':(i.payload,'status','other'),
        'quantity':(i.payload.rate,'value',Decimal('3')), 'unit':(i.payload.rate.unit,'raw','other'),
        'source':(i.provenance.source,'identifier','other'), 'time':(i.time,'event',AT+timedelta(days=1)),
        'scope':(scope(),'patient_id','other'), 'snapshot':(snapshot(),'disclosures',()),
        'metadata':(i.ingestion,'ingestion_sequence',3), 'parameter':(i.payload.parameters[0],'concept_id','other')}
    obj,key,v = objects[part]
    with pytest.raises(ValidationError): setattr(obj,key,v)


def test_input_lists_are_defensively_converted_and_not_retained():
    i = item('respiratory_support')
    parameters = [i.payload.parameters[0].model_dump()]
    p = replace(i.payload,parameters=parameters)
    parameters[0]['concept_id'] = 'mutated'
    assert p.parameters[0].concept_id == 'recorded-setting'
    items = [item()]
    result = snapshot(laboratory=items)
    items.clear()
    assert len(result.laboratory) == 1


@pytest.mark.parametrize('part', ['metadata_bool', 'metadata_negative', 'payload_extra', 'mutable_value', 'origin', 'naive_time', 'reference'])
def test_malformed_and_forged_nested_objects_revalidated(part):
    i = item()
    if part == 'metadata_bool': changes = dict(ingestion=i.ingestion.model_copy(update={'payload_version':True}))
    elif part == 'metadata_negative': changes = dict(ingestion=i.ingestion.model_copy(update={'ingestion_sequence':-1}))
    elif part == 'payload_extra': changes = dict(payload=i.payload.model_copy(update={'diagnosis':{'bad':[]}}))
    elif part == 'mutable_value': changes = dict(payload=i.payload.model_copy(update={'value':{'status':'known','value':{'untyped':[]}}}))
    elif part == 'origin': changes = dict(origin='inferred')
    elif part == 'naive_time': changes = dict(time=i.time.model_copy(update={'event':AT.replace(tzinfo=None)}))
    else: changes = dict(reference=i.reference.model_copy(update={'version':''}))
    with pytest.raises(ValueError): state.RetainedStateItem.model_validate(i.model_copy(update=changes))


def test_missing_ingestion_disclosed_without_claiming_durable_visibility():
    supplied = item(ingestion=None)
    assert snapshot(laboratory=(supplied,)).laboratory[0].ingestion is None
    with pytest.raises(ValueError): item(ingestion=None,disclosures=())


@pytest.mark.parametrize('origin_kind', ['inference','derived_value'])
def test_origin_cannot_be_laundered_by_provenance(origin_kind):
    provenance = replace(item().provenance,upstream=(LineageEdge(target=Reference(kind=origin_kind,id='parent',version='1'),relationship='derived_from'),))
    with pytest.raises(ValueError): item(provenance=provenance)


def test_no_self_dependency_and_no_implicit_snapshot_dependencies():
    i = item()
    provenance = replace(i.provenance, upstream=(LineageEdge(target=i.reference,relationship='copied_from'),))
    with pytest.raises(ValueError): replace(i,provenance=provenance)
    # Unresolved external source references remain disclosures, not an inferred graph.
    parent = Reference(kind='observation',id='prior-source',version='1')
    i = replace(i,provenance=replace(i.provenance,upstream=(LineageEdge(target=parent,relationship='copied_from'),)))
    assert snapshot(laboratory=(i,)).laboratory[0].provenance.dependencies == (parent,)
    assert not hasattr(snapshot(laboratory=(i,)), 'dependencies')


@pytest.mark.parametrize('mode', ['room air','supplemental oxygen','high-flow support','noninvasive support','invasive ventilation'])
def test_recorded_respiratory_modes_are_source_text(mode):
    assert state.RespiratorySupportState(mode=mode,status='recorded').mode == mode


@pytest.mark.parametrize('modality', ['no active support','intermittent therapy','continuous therapy'])
def test_recorded_renal_modalities_are_source_text(modality):
    assert state.RenalSupportState(modality=modality,status='recorded').modality == modality


@pytest.mark.parametrize('domain', ['medication','antimicrobial'])
def test_medication_missing_dose_and_conflicting_frequency(domain):
    p = payload(domain)
    assert replace(p,dose=None).frequency == p.frequency
    with pytest.raises(ValueError): replace(p,frequency=replace(p.frequency,occurrences=3))


def test_antimicrobial_distinct_and_recorded_context_only():
    p = payload('antimicrobial')
    assert p.domain == 'antimicrobial' and p.recorded_indication == 'recorded context'
    with pytest.raises(ValueError): replace(payload('medication'),recorded_indication='not medication contract')


@pytest.mark.parametrize('domain', ['hemodynamic_support','respiratory_support','renal_support'])
def test_duplicate_parameters_rejected(domain):
    i = item(domain)
    p = replace(i.payload,parameters=(i.payload.parameters[0],i.payload.parameters[0]))
    with pytest.raises(ValueError): replace(i,payload=p,payload_digest=sha256(canonical_payload(p).encode()).hexdigest())


def test_microbiology_no_specimen_and_unknown_result_semantics():
    with pytest.raises(ValueError): state.MicrobiologyState(result=ClinicalValue(status='known',value='reported'),status='final')
    p = replace(payload('microbiology'),result=ClinicalValue(status='missing',reason='not reported'),organisms=(),susceptibilities=())
    assert p.result.status == 'missing' and p.organisms == ()


def test_lossy_timestamp_rejected_without_normalization():
    offset = timezone(timedelta(hours=5,minutes=30,seconds=1))
    with pytest.raises(UnsupportedOperation): replace(scope(),review_start=AT.replace(tzinfo=offset))


def test_canonical_decimal_and_offset_exact():
    s = full_snapshot()
    raw = canonical_payload(s)
    assert '"value":"1.2300"' in raw and '"value":"-12.00"' in raw
    assert '"raw":" raw-unit "' in raw and '2026-10-08T08:00:00.123456+05:30' in raw
    assert canonical_payload(state.PatientStateSnapshot.model_validate_json(raw)) == raw
    assert 'canonical_digest' not in json.loads(raw) and 'ordered_items' not in json.loads(raw)


@pytest.mark.parametrize('seed', ['1','777'])
def test_hash_seed_independence(seed):
    root = Path(__file__).resolve().parents[1]
    script = 'from test_patient_state import full_snapshot,canonical_payload; s=full_snapshot(); print(canonical_payload(s)); print(s.canonical_digest)'
    proc = subprocess.run([sys.executable,'-c',script],check=True,text=True,capture_output=True,timeout=30,cwd=root,
        env={**os.environ,'PYTHONPATH':os.pathsep.join((str(root/'backend'),str(root/'tests'))),
             'PYTHONHASHSEED':seed,'PYTHONDONTWRITEBYTECODE':'1'})
    expected = full_snapshot()
    assert proc.stdout.splitlines() == [canonical_payload(expected),expected.canonical_digest]


def test_pure_contracts_no_repository_clock_or_governance(monkeypatch):
    import sqlite3
    import app.persistence.repository as repository
    import app.services.governance_service as governance
    def forbidden(*args, **kwargs): pytest.fail('M1 executed storage or governance')
    monkeypatch.setattr(sqlite3,'connect',forbidden)
    monkeypatch.setattr(repository.PatientRepository,'capture_cutoff',forbidden)
    monkeypatch.setattr(repository.PatientRepository,'list_history',forbidden)
    monkeypatch.setattr(governance,'assess_release',forbidden)
    monkeypatch.setattr(governance,'decide_release',forbidden)
    s = full_snapshot()
    assert state.PatientStateSnapshot.model_validate_json(canonical_payload(s)).canonical_digest == s.canonical_digest
    source = Path(state.__file__).read_text()
    tree = ast.parse(source)
    imports = [n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    assert not any('weight' in name or 'creatinine' in name or 'governance' in name or 'sqlalchemy' in name for name in imports)
    assert not any(word in source for word in ('ContextSnapshot', 'ClinicalInference(', 'datetime.now', 'time.time(', 'append_fact(', 'select_', 'execute_', 'tacrolimus', 'transplant', 'LDLT'))
    assert set(state.PatientStateSnapshot.model_fields) == {'scope',*DOMAINS,'disclosures'}


@pytest.mark.parametrize('basis,domain', [('contextual_history','history_event'), ('effective_interval','medication')])
def test_event_time_precedes_effective_start_in_display_order(basis, domain):
    later = item(domain,index=1,temporal_basis=basis,
        time=ClinicalTime(event=AT+timedelta(hours=1),effective_start=AT-timedelta(days=30),precision='instant'))
    earlier = item(domain,index=2,at=AT,temporal_basis=basis,
        time=ClinicalTime(event=AT,effective_start=AT-timedelta(days=1),precision='instant'))
    result = snapshot(**{domain:(later,earlier)})
    assert [i.reference.id for i in result.ordered_items] == ['fact-2','fact-1']
    assert getattr(result,domain) == (earlier,later)


def test_reversed_effective_instants_with_dst_fold_rejected():
    zone = ZoneInfo('America/New_York')
    # Wall times look ordered, but the actual instants run backward.
    start = datetime(2026,11,1,1,15,tzinfo=zone,fold=1)
    end = datetime(2026,11,1,1,30,tzinfo=zone,fold=0)
    with pytest.raises(ValueError):
        item('medication',temporal_basis='effective_interval',
             time=ClinicalTime(effective_start=start,effective_end=end,precision='instant'))
