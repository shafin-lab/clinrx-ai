from datetime import datetime, timezone
from hashlib import sha256

import pytest
from pydantic import ValidationError

from app.models.clinical.common import Binding, ClinicalTime, ContextTarget, IdentityVerification, Provenance, Reference, Source
from app.models.clinical.laboratory import LaboratoryComponent, LaboratoryReport
from app.models.clinical.recorded_v2 import RecordedTime, SourceCode
from app.persistence.repository import transaction
from app.persistence.history import FactIdentity
from app.persistence.bounded_history import HistoryBudget
from test_persistence import database, registered

AT = datetime(2026, 10, 8, 9, tzinfo=timezone.utc)
TARGET = ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e1')
SOURCE = Source(namespace='lab.example', identifier='system-a', version='1', channel='external_record')
PROVENANCE = Provenance(source=SOURCE, actor='synthetic-import', recorded_at=AT,
    lineage='unknown', limitations=('Synthetic source report.',))


def stamp(value):
    return RecordedTime(status='known', precision='instant', value=value)


def component(identity='c1', test='SODIUM', value='138.00', *, unit='mmol/L', mapping='sodium'):
    mapped = mapping in {'urea','bun','sodium','potassium','urine_appearance','urine_colour',
        'urine_specific_gravity','urine_ph','urine_protein','urine_glucose','urine_ketones',
        'urine_blood','urine_leukocyte_esterase','urine_nitrite','urine_bilirubin',
        'urine_urobilinogen','urine_rbc','urine_wbc','urine_epithelial_cells','urine_casts',
        'urine_crystals','urine_bacteria'}
    return LaboratoryComponent(source_component_id=identity,
        test_code=SourceCode(namespace='lab.example', code=test, version='1', raw_display=test),
        mapping_status='mapped' if mapped else 'unsupported', mapped_concept=mapping if mapped else None,
        mapping_version='synthetic-lab-map/1' if mapped else None,
        result={'kind':'numeric','raw_value':value,'comparator':'=','unit':
            ({'namespace':'unit.source','code':unit,'version':None,'raw_display':unit} if unit else None)},
        source_interference_flags=(), source_flags=())


def report(components=None, *, source_report='report-1', report_body=None, report_digest=None, revision='1', supersedes=None, change_state='original', report_status='final', correction_reason=None, fact_id='lab-report-1'):
    verification=IdentityVerification(status='verified',method='synthetic fixture mapping',
        verifier='synthetic-import',assessed_at=AT,source=SOURCE)
    return LaboratoryReport(kind='laboratory_report',id=fact_id,revision=revision,
        binding=Binding(target=TARGET,verification=verification),origin='reported',provenance=PROVENANCE,
        time=ClinicalTime(precision='unknown'),temporal_status='unknown',
        source_identity={'issuer_namespace':'lab.example','source_report_id':source_report,
            'source_version':revision,'accession_id':'accession-1'},
        report_status=report_status,change_state=change_state,supersedes=supersedes,correction_reason=correction_reason,
        times={'collected':stamp(AT),'received':RecordedTime(status='not_recorded'),
            'measured':RecordedTime(status='not_recorded'),'reported':stamp(AT),'available':stamp(AT)},
        specimen={'source_specimen_id':'specimen-1','specimen_type':{'namespace':'specimen.source','code':'serum','version':None,'raw_display':'Serum'},'collection_site':None},
        components=components or (component(),),original_report=report_body,
        original_report_digest=report_digest if report_digest is not None else sha256(report_body.encode()).hexdigest() if report_body else None)


def test_lab_report_retains_exact_numeric_lexeme_unit_and_source_times():
    item=report()
    assert item.components[0].result.raw_value=='138.00'
    assert item.components[0].result.unit.raw_display=='mmol/L'
    assert item.times.available.value==AT
    assert item.source_identity.source_report_id=='report-1'


def test_missing_unit_and_unmapped_test_remain_explicit_not_normalized():
    item=report((component('c1','LOCAL-SODIUM','138',unit=None,mapping='unknown'),))
    assert item.components[0].result.unit is None
    assert item.components[0].mapping_status=='unsupported'
    assert item.components[0].mapped_concept is None


def test_report_requires_exact_component_identity_and_unique_components():
    with pytest.raises(ValidationError):
        report((component('c1'),component('c1')))


def test_raw_report_digest_must_match_retained_source_bytes():
    with pytest.raises(ValidationError):
        report(report_body='Original source bytes', report_digest='0'*64)


def test_numeric_values_reject_float_and_nonfinite_lexemes():
    with pytest.raises(ValidationError):
        component(value=138.0)
    with pytest.raises(ValidationError):
        component(value='NaN')


def test_source_correction_uses_same_report_identity_and_explicit_predecessor():
    prior=report()
    corrected=report(source_report='report-1', revision='2', supersedes=prior.reference,
        change_state='corrected', report_status='corrected', correction_reason='Issuer corrected report.')
    assert corrected.supersedes==Reference(kind='laboratory_report',id='lab-report-1',version='1')
    assert corrected.source_identity.issuer_namespace==prior.source_identity.issuer_namespace
    assert corrected.source_identity.source_report_id==prior.source_identity.source_report_id
    assert corrected.source_identity.accession_id==prior.source_identity.accession_id
    assert corrected.source_identity.source_version=='2'


def test_report_revisions_persist_and_remain_bounded_by_repository_cutoff(registered):
    prior = report()
    with transaction(registered) as repo:
        before = repo.capture_cutoff()
        saved = repo.append_fact(prior, target=TARGET)
        first_cutoff = repo.capture_cutoff()
    corrected = report(revision='2', supersedes=prior.reference,
        change_state='corrected', report_status='corrected', correction_reason='Issuer corrected report.')
    with transaction(registered) as repo:
        corrected_saved = repo.append_revision(corrected, target=TARGET)
        after = repo.capture_cutoff()
        old = repo.list_bounded_history(target=TARGET, cutoff=first_cutoff,
            budget=HistoryBudget(), identity=FactIdentity(kind='laboratory_report', id=prior.id))
        current = repo.list_bounded_history(target=TARGET, cutoff=after,
            budget=HistoryBudget(), identity=FactIdentity(kind='laboratory_report', id=prior.id))
    assert saved.fact == prior and corrected_saved.fact == corrected
    assert before.fact_watermark < first_cutoff.fact_watermark < after.fact_watermark
    assert [row.fact.reference for row in old.records] == [prior.reference]
    assert [row.fact.reference for row in current.records] == [prior.reference, corrected.reference]
