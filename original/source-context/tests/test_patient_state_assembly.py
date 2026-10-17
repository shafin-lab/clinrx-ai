"""Synthetic source-backed assembly, independently asserted at real SQLite boundaries."""
from contextlib import contextmanager
from dataclasses import replace as dc_replace
from datetime import timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from app.execution import patient_state_assembly as assembly
from app.execution.patient_state import PatientStateScope
from app.models.clinical.common import ClinicalTime, ClinicalValue, Quantity, Unit
from app.models.clinical.facts import Frequency
from app.persistence.errors import (PersistenceInputError, ScopeMismatch, StorageIntegrityError,
                                    TransactionAborted, RecordNotFound)
from app.persistence.mapping import canonical_payload
from app.persistence.repository import PatientRepository, transaction
from test_persistence import AT, TARGET, ROOT, database, registered, fact, replace
from test_revision_chains import revision


def lab(id='lab', value='1.2300', at=AT):
    base = fact(id=id, concept_id='synthetic-serum-creatinine',
        time=ClinicalTime(event=at, recorded=at+timedelta(hours=1), precision='instant'),
        value=ClinicalValue(status='known', value=Quantity(value=Decimal(value),
            unit=Unit(raw='mg/dL', status='assessed', system='UCUM', code='mg/dL'))))
    return replace(base, provenance=replace(base.provenance,
        source=replace(base.provenance.source, namespace='clinrx.synthetic.serum-creatinine', version='1')))


def med(kind='medication_order', at=AT, **kwargs):
    changes = dict(time=ClinicalTime(event=at, recorded=AT+timedelta(days=1), precision='instant'))
    if kind == 'medication_administration':
        changes.update(administered_at=at, provenance=replace(fact(kind).provenance, recorded_at=AT+timedelta(days=1)))
    changes.update(kwargs)
    return fact(kind, **changes)


def save(engine, *facts):
    with transaction(engine) as repo:
        for source in facts:
            repo.append_fact(source, target=source.binding.target)
        return repo.capture_cutoff()


def scope(cutoff, **kwargs):
    return PatientStateScope(patient_id=TARGET.patient_id, encounter_id=TARGET.encounter_id,
        review_start=AT, review_end=AT+timedelta(hours=2), repository_cutoff=cutoff, **kwargs)


def run(engine, cutoff, **kwargs):
    return assembly.assemble_patient_state(engine, scope=scope(cutoff, **kwargs))


@pytest.mark.parametrize('count', [0, 1, 2, 4])
def test_zero_to_many_and_exact_coverage(registered, count):
    result = run(registered, save(registered, *(lab(str(i)) for i in range(count))))
    assert len(result.snapshot.laboratory) == count
    assert [c.domain for c in result.coverage] == ['laboratory','medication','antimicrobial',
        'hemodynamic_support','respiratory_support','renal_support','fluid_output','microbiology','procedure','history_event']
    assert result.profile_id == 'SyntheticLaboratoryMedicationState' and result.profile_version == '1'
    assert result.coverage[0].mapping_support == 'partial'
    assert result.coverage[0].candidate_count == result.coverage[0].retained_count == count
    assert result.coverage[1].mapping_support == 'supported' and result.coverage[1].candidate_count == 0
    assert all(c.source_completeness == 'unknown' for c in result.coverage)
    for c in result.coverage[2:]:
        assert c.mapping_support == 'unsupported' and c.retrieval == 'not_attempted'
        assert (c.candidate_count, c.retained_count, c.unsuitable_count) == (None, None, None)
    assert 'clinical absence' in result.snapshot.disclosures[1]
    assert 'Availability by clinical time is not established' in result.snapshot.disclosures[3]


@pytest.mark.parametrize('value', ['0', '-1.200', '1.2300'])
def test_laboratory_is_representation_not_comparison_policy(registered, value):
    source = lab(value=value)
    result = run(registered, save(registered, source))
    item = result.snapshot.laboratory[0]
    assert item.reference == source.reference and item.provenance == source.provenance
    assert item.time == source.time and item.binding == source.binding
    assert item.conflict == 'unresolved' and item.verification == 'clinician_confirmed'
    assert str(item.payload.value.value.value) == value
    assert item.payload.specimen is None and item.payload.status is None
    assert item.payload_digest == sha256(canonical_payload(item.payload).encode()).hexdigest()
    assert item.ingestion.ingestion_sequence == 1
    assert 'Source uncertainty: synthetic uncertainty' in item.disclosures


@pytest.mark.parametrize('kind', ['laboratory', 'medication_order', 'medication_administration'])
@pytest.mark.parametrize('offset,retained', [(0,True),(7200,True),(-0.000001,False),(7200.000001,False)])
def test_closed_event_boundaries(registered, kind, offset, retained):
    at = AT+timedelta(seconds=offset)
    source = lab(at=at) if kind == 'laboratory' else med(kind, at=at)
    result = run(registered, save(registered, source))
    assert len(result.snapshot.ordered_items) == int(retained)
    assert [i.reason for i in result.issues] == ([] if retained else ['outside_review_window'])
    assert sum(c.unsuitable_count or 0 for c in result.coverage) == 0


def test_zero_width_and_offset_retention(registered):
    source = lab(at=AT.astimezone(timezone(timedelta(hours=5,minutes=30))))
    cutoff = save(registered, source)
    result = assembly.assemble_patient_state(registered, scope=replace(scope(cutoff), review_end=AT))
    assert result.snapshot.laboratory[0].time.event.isoformat() == source.time.event.isoformat()
    raw = canonical_payload(result)
    assert canonical_payload(assembly.PatientStateAssemblyResult.model_validate_json(raw)) == raw


@pytest.mark.parametrize('start,end,retained', [(-1,0,True),(2,3,True),(-1,3,True),(-1,None,True),(-2,-1,False),(3,None,False)])
def test_order_intervals(registered, start, end, retained):
    source = med(time=ClinicalTime(effective_start=AT+timedelta(hours=start),
        effective_end=None if end is None else AT+timedelta(hours=end), precision='instant'), order_status='held')
    result = run(registered, save(registered, source))
    assert len(result.snapshot.medication) == int(retained)
    if retained:
        item = result.snapshot.medication[0]
        assert item.temporal_basis == 'effective_interval' and item.payload.status == 'held'
        assert item.time.effective_end == source.time.effective_end
        assert 'does not establish currently active therapy' in item.disclosures[-1]


def test_interval_membership_but_event_first_order_and_full_dose(registered):
    a = med(id='a', at=AT+timedelta(hours=1),
        time=ClinicalTime(event=AT+timedelta(hours=1), effective_start=AT-timedelta(days=10), precision='instant'))
    frequency = Frequency(occurrences=2, interval=Quantity(value=Decimal('24.00'), unit=Unit(raw='hours', status='unresolved', limitation='source')))
    a = replace(a, prescribed_dose=replace(a.prescribed_dose, frequency=frequency))
    b = med(id='b')
    result = run(registered, save(registered, a, b))
    assert [i.reference.id for i in result.snapshot.medication] == ['b','a']
    mapped = result.snapshot.medication[1].payload
    assert mapped.dose == a.prescribed_dose and mapped.frequency == frequency
    assert mapped.route == a.route and mapped.schedule_text == a.schedule_text


def test_administration_semantics_and_no_drug_classification(registered):
    source = med('medication_administration')
    result = run(registered, save(registered, source))
    item = result.snapshot.medication[0]
    assert item.payload.status == 'administered'
    assert item.payload.dose == source.administered_dose and item.payload.route == source.route
    assert item.time.event == source.administered_at
    assert result.snapshot.antimicrobial == result.snapshot.hemodynamic_support == ()


@pytest.mark.parametrize('change,reason', [
    ('missing','missing_required_event_time'), ('day','unsupported_temporal_precision'),
    ('approximate','unsupported_temporal_precision'), ('unknown','unsupported_temporal_precision'),
    ('uncertain','unsupported_temporal_precision'), ('text','structurally_unsuitable_source_shape'),
    ('missing_value','structurally_unsuitable_source_shape'), ('concept','unsupported_source_profile'),
    ('namespace','unsupported_source_profile'), ('version','unsupported_source_profile'), ('channel','unsupported_source_profile')])
def test_structural_issues_and_counts(registered, change, reason):
    source = lab()
    if change == 'missing': source = replace(source,time=replace(source.time,event=None))
    elif change in ('day','approximate','unknown'): source = replace(source,time=replace(source.time,precision=change))
    elif change == 'uncertain': source = replace(source,time=replace(source.time,uncertainty='source says uncertain'))
    elif change == 'text': source = replace(source,value=ClinicalValue(status='known',value='PRIVATE_SOURCE_CONTENT'))
    elif change == 'missing_value': source = replace(source,value=ClinicalValue(status='missing',reason='not reported'))
    elif change == 'concept': source = replace(source,concept_id='unmapped')
    else:
        source = replace(source,provenance=replace(source.provenance,
            source=replace(source.provenance.source, **{change:'clinician' if change == 'channel' else 'other'})))
    result = run(registered, save(registered, source))
    assert result.snapshot.laboratory == ()
    assert [(i.reference,i.reason) for i in result.issues] == [(source.reference,reason)]
    assert result.coverage[0].candidate_count == 1
    assert result.coverage[0].unsuitable_count == int(reason != 'unsupported_source_profile')
    assert 'PRIVATE_SOURCE_CONTENT' not in canonical_payload(result.issues[0])


@pytest.mark.parametrize('change', ['concept','outside','shape','same_value'])
def test_terminal_before_mapping_and_old_prefix(registered, change):
    first = lab()
    cutoff = save(registered,first,med())
    before = run(registered,cutoff)
    updates = {'concept_id':'other'} if change == 'concept' else {'time':replace(first.time,event=AT+timedelta(days=2))} if change == 'outside' else {'value':ClinicalValue(status='known',value='unsupported')} if change == 'shape' else {}
    with transaction(registered) as repo:
        corrected = repo.append_revision(revision(first,'second',**updates),target=TARGET)
        later = repo.capture_cutoff()
    assert canonical_payload(run(registered,cutoff)) == canonical_payload(before)
    after = run(registered,later)
    assert after.snapshot.medication == before.snapshot.medication
    if change == 'same_value':
        a,b = before.snapshot.laboratory[0],after.snapshot.laboratory[0]
        assert a.payload_digest == b.payload_digest and a.reference != b.reference
        assert a.canonical_digest != b.canonical_digest and b.ingestion == corrected.ingestion
    else:
        assert after.snapshot.laboratory == ()
        assert after.issues[0].reference == corrected.fact.reference


@pytest.mark.parametrize('case', ['repository','oversized','bool','encounter','patient','missing'])
def test_scope_errors(registered, case):
    cutoff = save(registered,lab())
    s = scope(cutoff)
    if case in ('repository','oversized','bool'):
        c = cutoff.model_copy(update={'repository_id':uuid4()} if case == 'repository' else {'fact_watermark':True if case == 'bool' else 9999})
        s = s.model_copy(update={'repository_cutoff':c})
    else:
        s = s.model_copy(update={'patient_id':'synthetic-p2'} if case == 'patient' else {'encounter_id':'missing' if case == 'missing' else 'synthetic-e3'})
    expected = PersistenceInputError if case in ('oversized','bool') else RecordNotFound if case == 'missing' else ScopeMismatch
    with pytest.raises(expected): assembly.assemble_patient_state(registered,scope=s)


@pytest.mark.parametrize('change', ['same','payload','metadata','revision'])
def test_exact_duplicate_contract(registered,monkeypatch,change):
    cutoff = save(registered,lab())
    original = PatientRepository.list_bounded_history
    def repeated(self, **kwargs):
        result = original(self, **kwargs)
        stored = result.records[0]
        other = stored
        if change == 'payload': other = dc_replace(stored,fact=replace(stored.fact,uncertainty=('different',)))
        if change == 'metadata': other = dc_replace(stored,ingestion=replace(stored.ingestion,ingested_at=AT))
        if change == 'revision': other = dc_replace(stored,fact=revision(stored.fact,'other'))
        return dc_replace(result,records=(stored,other))
    monkeypatch.setattr(PatientRepository,'list_bounded_history',repeated)
    if change == 'same':
        result = run(registered,cutoff)
        assert result.coverage[0].candidate_count == result.coverage[0].retained_count == 1
    else:
        with pytest.raises(StorageIntegrityError): run(registered,cutoff)


def test_equal_values_distinct_sources_retained_and_issues_ordered(registered):
    a,b = lab('a'),lab('b')
    sources = [lab('z'),lab('c')]
    sources = [replace(s,concept_id='unknown') for s in sources]
    result = run(registered,save(registered,b,*sources,a))
    assert [i.reference.id for i in result.snapshot.laboratory] == ['a','b']
    assert [i.reference.id for i in result.issues] == ['c','z']
    assert result.coverage[0].candidate_count == 4 and result.coverage[0].unsuitable_count == 0


def test_one_read_one_transaction_no_clock_no_dml(registered,monkeypatch):
    import app.persistence.repository as repository
    cutoff = save(registered,lab(),med())
    sql, calls = [],[]
    def observe(conn,cursor,statement,parameters,context,executemany): sql.append(statement)
    event.listen(registered,'before_cursor_execute',observe)
    original = PatientRepository.list_bounded_history
    def read(self, **kwargs):
        calls.append(kwargs)
        return original(self,**kwargs)
    def forbidden(*args,**kwargs): pytest.fail('forbidden clock or cutoff capture')
    monkeypatch.setattr(repository,'_now',forbidden)
    monkeypatch.setattr(PatientRepository,'capture_cutoff',forbidden)
    monkeypatch.setattr(PatientRepository,'list_bounded_history',read)
    try: result = run(registered,cutoff)
    finally: event.remove(registered,'before_cursor_execute',observe)
    assert len(calls)==1
    assert calls[0]['target']==TARGET and calls[0]['cutoff']==cutoff and calls[0]['latest'] is True
    assert calls[0]['budget'].max_rows==4096 and calls[0]['accounting'].rows==2
    assert sum(s == 'BEGIN IMMEDIATE' for s in sql) == 1
    assert not any(s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','CREATE','ALTER','DROP')) for s in sql)
    assert len(result.snapshot.ordered_items) == 2


def test_later_concurrent_writer_cannot_enter_assembly(registered,monkeypatch):
    cutoff = save(registered,lab())
    original = PatientRepository.list_bounded_history
    attempted=[]
    def read(self,**kwargs):
        import sqlite3
        with sqlite3.connect(registered.url.database,timeout=0) as competing:
            with pytest.raises(sqlite3.OperationalError,match='locked'):
                competing.execute('BEGIN IMMEDIATE')
        attempted.append(True)
        return original(self,**kwargs)
    monkeypatch.setattr(PatientRepository,'list_bounded_history',read)
    assert len(run(registered,cutoff).snapshot.laboratory) == 1
    assert attempted == [True]


@pytest.mark.parametrize('failure', ['corrupt','read','mapper','exit','interrupt'])
def test_failures_never_become_empty_success(registered,monkeypatch,failure):
    cutoff = save(registered,lab())
    if failure == 'corrupt':
        with registered.begin() as conn: conn.execute(text("UPDATE fact_revision SET payload='PRIVATE_BROKEN_JSON'"))
        expected=StorageIntegrityError
    elif failure == 'exit':
        original=assembly.transaction
        @contextmanager
        def broken(engine):
            with original(engine) as repo: yield repo
            raise RuntimeError('PRIVATE_DRIVER_CONTENT')
        monkeypatch.setattr(assembly,'transaction',broken)
        expected=TransactionAborted
    else:
        expected=KeyboardInterrupt if failure == 'interrupt' else TransactionAborted
        def broken(*args,**kwargs):
            if failure == 'interrupt': raise KeyboardInterrupt()
            raise RuntimeError('PRIVATE_DRIVER_CONTENT')
        monkeypatch.setattr(assembly,'_map',broken) if failure in ('mapper','interrupt') else monkeypatch.setattr(PatientRepository,'list_bounded_history',broken)
    with pytest.raises(expected) as caught: run(registered,cutoff)
    assert 'PRIVATE_DRIVER_CONTENT' not in ''.join(traceback.format_exception(caught.value))
    assert 'PRIVATE_BROKEN_JSON' not in ''.join(traceback.format_exception(caught.value))


def test_foreign_corruption_and_future_corruption_do_not_leak(registered):
    source=lab()
    cutoff=save(registered,source)
    foreign=replace(lab('foreign'),binding=replace(source.binding,target=replace(TARGET,encounter_id='synthetic-e2')))
    with transaction(registered) as repo:
        repo.append_fact(foreign,target=foreign.binding.target)
        future=repo.append_revision(revision(source,'2'),target=TARGET)
        later=repo.capture_cutoff()
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='bad' WHERE ingestion_sequence > :s"),{'s':cutoff.fact_watermark})
    assert run(registered,cutoff).snapshot.laboratory[0].reference == source.reference
    with pytest.raises(StorageIntegrityError): run(registered,later)


@pytest.mark.parametrize('case',['counts','coverage_order','unsupported_counts','snapshot_disclosures','profile','mutable'])
def test_result_contract_rejects_forgery(registered,case):
    result=run(registered,save(registered,lab()))
    if case=='counts': updates={'coverage':(result.coverage[0].model_copy(update={'candidate_count':99}),*result.coverage[1:])}
    elif case=='coverage_order': updates={'coverage':tuple(reversed(result.coverage))}
    elif case=='unsupported_counts': updates={'coverage':(*result.coverage[:2],result.coverage[2].model_copy(update={'retained_count':0}),*result.coverage[3:])}
    elif case=='snapshot_disclosures': updates={'snapshot':result.snapshot.model_copy(update={'disclosures':()})}
    elif case=='profile': updates={'profile_version':'2'}
    else: updates={'issues':({'reference':{},'domain':'laboratory','reason':{'bad':[]}},)}
    with pytest.raises(ValueError): assembly.PatientStateAssemblyResult.model_validate(result.model_copy(update=updates))
    with pytest.raises(ValidationError): result.snapshot.laboratory[0].payload.value.value.value=Decimal('9')


@pytest.mark.parametrize('seed',['1','777'])
def test_reopen_process_hashseed_representation(registered,seed):
    cutoff=save(registered,lab(),med())
    expected=canonical_payload(run(registered,cutoff))
    script='''import sys
from app.persistence.database import create_database
from app.execution.patient_state import PatientStateScope
from app.execution.patient_state_assembly import assemble_patient_state
from app.persistence.mapping import canonical_payload
engine=create_database(sys.argv[1])
print(canonical_payload(assemble_patient_state(engine,scope=PatientStateScope.model_validate_json(sys.argv[2]))))
engine.dispose()
'''
    completed=subprocess.run([sys.executable,'-c',script,registered.url.database,scope(cutoff).model_dump_json()],
        capture_output=True,text=True,check=True,timeout=30,
        env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'PYTHONHASHSEED':seed,'PYTHONDONTWRITEBYTECODE':'1'})
    assert completed.stdout.strip()==expected


def test_no_capability_or_governance_imports():
    source=Path(assembly.__file__).read_text()
    imports=[n.module for n in ast.walk(ast.parse(source)) if isinstance(n,ast.ImportFrom)]
    assert not any(any(word in name for word in ('weight','creatinine','governance','lineage','executions')) for name in imports)
    assert all(word not in source for word in ('ClinicalInference(', 'derived_from', 'assess_release(', 'decide_release(', 'resolve_lineage(', 'capture_cutoff(', 'datetime.now('))


def test_availability_and_capture_time_do_not_filter_clinical_window(registered):
    source=lab()
    source=replace(source,time=replace(source.time,recorded=AT+timedelta(days=10),
        retrieved=AT+timedelta(days=11),processed=AT+timedelta(days=12)))
    cutoff=save(registered,source)
    cutoff=replace(cutoff,captured_at=AT-timedelta(days=10))
    result=run(registered,cutoff)
    assert result.snapshot.laboratory[0].time == source.time
    assert result.snapshot.scope.repository_cutoff == cutoff
    assert result.snapshot.laboratory[0].ingestion.ingested_at != source.time.event


@pytest.mark.parametrize('precision,retained',[('day',True),('approximate',True),('unknown',False)])
def test_interval_precision_is_disclosed_not_reinterpreted(registered,precision,retained):
    source=med(time=ClinicalTime(effective_start=AT,precision=precision,uncertainty='recorded uncertainty'))
    result=run(registered,save(registered,source))
    assert len(result.snapshot.medication)==int(retained)
    if retained:
        assert result.snapshot.medication[0].time==source.time
        assert 'representative endpoints' in result.snapshot.medication[0].disclosures[-1]
    else:
        assert result.issues[0].reason=='unsupported_temporal_precision'
        assert result.coverage[1].unsuitable_count==1


def test_missing_order_time_and_inference_are_not_invented_domains(registered):
    order=med(time=ClinicalTime(precision='unknown'))
    inference=fact('inference')
    result=run(registered,save(registered,order,inference))
    assert result.snapshot.ordered_items==()
    assert [(i.domain,i.reason) for i in result.issues]==[
        (None,'unsupported_source_profile'),('medication','missing_required_event_time')]
    assert result.coverage[1].candidate_count==result.coverage[1].unsuitable_count==1
    assert all(c.candidate_count is None for c in result.coverage[2:])


@pytest.mark.parametrize('part',['target','cutoff','selection','record_scope'])
def test_inconsistent_history_result_aborts(registered,monkeypatch,part):
    cutoff=save(registered,lab())
    original=PatientRepository.list_bounded_history
    def inconsistent(self,**kwargs):
        result=original(self,**kwargs)
        if part=='target': return dc_replace(result,target=replace(TARGET,encounter_id='synthetic-e2'))
        if part=='cutoff': return dc_replace(result,cutoff=replace(cutoff,captured_at=AT))
        if part=='selection': return dc_replace(result,selection='history')
        stored=result.records[0]
        foreign=replace(stored.fact,binding=replace(stored.fact.binding,target=replace(TARGET,encounter_id='synthetic-e2')))
        return dc_replace(result,records=(dc_replace(stored,fact=foreign),))
    monkeypatch.setattr(PatientRepository,'list_bounded_history',inconsistent)
    with pytest.raises(StorageIntegrityError): run(registered,cutoff)


@pytest.mark.parametrize('bad',[None,object(),'database.sqlite3'])
def test_engine_only_boundary(registered,bad):
    cutoff=save(registered)
    with pytest.raises(PersistenceInputError): run(bad,cutoff)


def test_unresolved_unit_is_retained_without_conversion(registered):
    source=lab()
    source=replace(source,value=replace(source.value,value=replace(source.value.value,
        unit=Unit(raw=' source-unit ',status='unresolved',limitation='uninterpreted source'))))
    result=run(registered,save(registered,source))
    assert result.snapshot.laboratory[0].payload.value==source.value
    assert '"value":"1.2300"' in canonical_payload(result)


def test_dst_point_order_uses_actual_instant(registered):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    zone=ZoneInfo('America/New_York')
    early=datetime(2026,11,1,1,45,tzinfo=zone,fold=0)
    late=datetime(2026,11,1,1,15,tzinfo=zone,fold=1)
    cutoff=save(registered,lab('late',at=late),lab('early',at=early))
    s=replace(scope(cutoff),review_start=early,review_end=late)
    result=assembly.assemble_patient_state(registered,scope=s)
    assert [i.reference.id for i in result.snapshot.laboratory]==['early','late']
    assert [i.time.event.isoformat() for i in result.snapshot.laboratory]==[early.isoformat(),late.isoformat()]
