"""M7 durable admission, source isolation, temporal reconstruction and bounds."""
from datetime import timedelta
import pytest
from sqlalchemy import text
from app.persistence.repository import transaction
from app.persistence.history import FactIdentity
from app.persistence.bounded_history import HistoryBudget, AggregateHistoryBudget, HistoryAccounting
from app.persistence.errors import QueryLimitExceeded, ScopeMismatch, StorageIntegrityError
from app.persistence.canonical import canonical_payload
from app.execution.patient_state_v3 import PatientStateScopeV3
from app.execution.patient_state_v3_assembly import AssemblyRequestV3, AssemblyLimitsV3, assemble_patient_state_v3
from test_persistence import database, registered
from test_patient_state_v3 import records, measurement, change, AT, TARGET, h, stamp, PROV


def save(engine,*facts):
    with transaction(engine) as repo:
        for f in facts:
            (repo.append_revision if f.supersedes else repo.append_fact)(f,target=TARGET)
        return repo.capture_cutoff()


def revised(f, **kw):
    fields = dict(revision='2', supersedes=f.reference, correction_reason='synthetic correction')
    if isinstance(f,h.LactateResult): fields['change']='corrected'
    fields.update(kw)
    return change(f,**fields)


def request(cutoff, **kw):
    return AssemblyRequestV3(scope=PatientStateScopeV3(patient_id=TARGET.patient_id,
        encounter_id=TARGET.encounter_id,review_start=AT,review_end=AT,repository_cutoff=cutoff),**kw)


@pytest.mark.parametrize('index', range(15))
def test_every_family_persists_corrects_and_reopens(registered,index):
    f = records()[index]
    before=save(registered,f)
    after=save(registered,revised(f))
    registered.dispose()
    with transaction(registered) as repo:
        retained=repo.load_fact(f.reference,target=TARGET)
        assert canonical_payload(retained.fact)==canonical_payload(f)
        assert retained.ingestion.ingestion_sequence==before.fact_watermark
        identity=FactIdentity(kind=f.kind,id=f.id)
        assert repo.load_latest_known(identity,target=TARGET,cutoff=before).records[0].fact.reference==f.reference
        assert repo.load_latest_known(identity,target=TARGET,cutoff=after).records[0].fact.revision=='2'
    view=assemble_patient_state_v3(registered,request=request(before))
    assert view.snapshot.items[0].reference==f.reference


def test_terminal_before_filter_and_cutoff_stability(registered):
    p=measurement()
    before=save(registered,p)
    after=save(registered,revised(p,record_status='withdrawn'))
    old=assemble_patient_state_v3(registered,request=request(before))
    current=assemble_patient_state_v3(registered,request=request(after))
    assert old.snapshot.items[0].reference.version=='1'
    assert current.snapshot.items[0].reference.version=='2'
    assert current.snapshot.items[0].fact.record_status=='withdrawn'
    assert 'withdrawn_terminal' in [i.reason for i in current.snapshot.issues]
    assert assemble_patient_state_v3(registered,request=request(before)).canonical_digest==old.canonical_digest


@pytest.mark.parametrize('dimension', ['rows','bytes','items','result'])
def test_resource_exhaustion_is_exception_not_withheld(registered,dimension):
    cutoff=save(registered,*records())
    limits = dict(history=HistoryBudget(max_rows=1)) if dimension=='rows' else (
        dict(history=HistoryBudget(max_payload_bytes=1)) if dimension=='bytes' else
        dict(max_items=1) if dimension=='items' else dict(max_result_bytes=1))
    with pytest.raises(QueryLimitExceeded):
        assemble_patient_state_v3(registered,request=request(cutoff,limits=AssemblyLimitsV3(**limits)))


def test_aggregate_read_accounting_charges_repeats(registered):
    cutoff=save(registered,measurement())
    accounting=HistoryAccounting(AggregateHistoryBudget(max_rows=1))
    assemble_patient_state_v3(registered,request=request(cutoff),accounting=accounting)
    with pytest.raises(QueryLimitExceeded):
        assemble_patient_state_v3(registered,request=request(cutoff),accounting=accounting)


def test_visible_corruption_not_missingness(registered):
    cutoff=save(registered,measurement())
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='invalid private payload'"))
    with pytest.raises(StorageIntegrityError):
        assemble_patient_state_v3(registered,request=request(cutoff))


def test_unknown_times_quality_retained_and_collection_not_substituted(registered):
    l=change(records()[7], collected=h.ClinicalInstant())
    cutoff=save(registered,l)
    view=assemble_patient_state_v3(registered,request=request(cutoff))
    assert view.snapshot.items[0].inclusion=='unplaced'
    assert view.snapshot.items[0].fact.measured.recorded.status=='not_recorded'
    assert view.snapshot.items[0].fact.collected.recorded.status=='not_recorded'


def test_exact_context_binding_and_cycle(registered):
    parent=change(records()[11],occurred=stamp(AT-timedelta(days=1)))
    p=measurement(associations=(h.EvidenceBinding(role='calibration',scope=TARGET,status='resolved',
        exact=parent.reference,provenance=PROV),))
    cutoff=save(registered,parent,p)
    view=assemble_patient_state_v3(registered,request=request(cutoff))
    assert [i.inclusion for i in view.snapshot.items]==['contextual','in_window']
    corrected=revised(parent,associations=(h.EvidenceBinding(role='context',scope=TARGET,status='resolved',
        exact=p.reference,provenance=PROV),))
    newer=revised(p,associations=(h.EvidenceBinding(role='calibration',scope=TARGET,status='resolved',
        exact=corrected.reference,provenance=PROV),))
    # This history has no cycle: the parent points to historical P1, not P2.
    cutoff=save(registered,corrected,newer)
    assert 'historical_association' in [i.reason for i in assemble_patient_state_v3(registered,request=request(cutoff)).snapshot.issues]


def test_future_correction_does_not_decode_at_original_prefix(registered):
    p=measurement();cutoff=save(registered,p)
    save(registered,revised(p))
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='future corrupt' WHERE revision='2'"))
    assert assemble_patient_state_v3(registered,request=request(cutoff)).snapshot.items[0].reference==p.reference


def test_v2_admission_not_expanded(registered):
    from app.execution.patient_state_v2 import PatientStateScopeV2
    from app.execution.patient_state_v2_assembly import AssemblyRequestV2,assemble_patient_state_v2
    cutoff=save(registered,measurement())
    scope=PatientStateScopeV2(patient_id=TARGET.patient_id,encounter_id=TARGET.encounter_id,
        review_start=AT,review_end=AT,repository_cutoff=cutoff)
    result=assemble_patient_state_v2(registered,request=AssemblyRequestV2(scope=scope,
        profile_id='SyntheticMicrobiologyAntimicrobialState',profile_version='2'))
    assert result.snapshot.items==()
    assert result.issues[0].reason=='unsupported_source_structure'


def test_moved_terminal_outside_window_never_resurrects(registered):
    p=measurement();save(registered,p)
    cutoff=save(registered,revised(p,occurred=stamp(AT+timedelta(days=1))))
    view=assemble_patient_state_v3(registered,request=request(cutoff))
    assert view.snapshot.items==()
    assert [i.reference.version for i in view.snapshot.issues if i.reason=='outside_window']==['2']


def test_closed_boundary_includes_exact_end_and_excludes_one_microsecond_later(registered):
    cutoff=save(registered,measurement(),measurement(name='after',occurred=stamp(AT+timedelta(microseconds=1))))
    view=assemble_patient_state_v3(registered,request=request(cutoff))
    assert tuple(i.reference.id for i in view.snapshot.items)==('p',)
    assert view.snapshot.coverage.candidate_rows==2 and view.snapshot.coverage.retained_count==1
