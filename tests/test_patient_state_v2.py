"""Pure M6.1 contracts: independently asserted boundaries, no persistence fixtures."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from uuid import UUID
from zoneinfo import ZoneInfo
import json

import pytest
from pydantic import ValidationError
from app.models.clinical.common import (Binding, ClinicalTime, ContextTarget,
    IdentityVerification, Provenance, Reference, Source, Unit)
from app.models.clinical import recorded_v2 as c, microbiology as m, antimicrobials as a
from app.execution import patient_state_v2 as s
from app.persistence.mapping import canonical_payload, validate_fact
from app.persistence.errors import UnsupportedOperation
from app.persistence.metadata import RepositoryCutoff, IngestionMetadata

AT = datetime(2026, 10, 8, 8, 0, 0, 123456, tzinfo=timezone(timedelta(hours=5, minutes=30)))
TARGET = ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e1')
SOURCE = Source(namespace='synthetic.lab', identifier='source-1', version='1', channel='external_record')
PROV = Provenance(source=SOURCE, actor='source', recorded_at=AT, lineage='unknown', limitations=('source assertion only',))
BIND = Binding(target=TARGET, verification=IdentityVerification(status='verified', method='synthetic', verifier='fixture', assessed_at=AT, source=SOURCE))
REPO = UUID('00000000-0000-4000-8000-000000000001')


def change(model, **values):
    return type(model).model_validate({**model.model_dump(), **values})


def time(at=AT):
    return c.RecordedTime(status='known', precision='instant', value=at)


def concept(raw='recorded label'):
    return c.RecordedConcept(raw_display=raw)


def code(raw='source-id', namespace='synthetic.lab'):
    return c.SourceCode(namespace=namespace, code=raw, version='v1', raw_display=' Raw display ')


def quantity(value='1.00', unit='mg/L'):
    return dict(value=value, unit=Unit(raw=unit, status='unresolved', limitation='source unit'))


def drug():
    return a.AntimicrobialIdentity(source_code=code('drug-1'), raw_display=' Source DRUG ', canonical_id='ingredient:1', ingredient_ids=('ingredient:1',), mapping_status='mapped', mapping_provenance=PROV)


def base(id):
    return dict(id=id, revision='1', binding=BIND, origin='reported', provenance=PROV,
        time=ClinicalTime(precision='unknown'), temporal_status='unknown')


def binding(role='specimen', id='S', kind=None):
    kind = kind or c.ROLE_KINDS[role][0]
    return c.DomainBinding(role=role, scope=TARGET, status='resolved', stable_target=c.StableIdentity(kind=kind,id=id), exact=Reference(kind=kind,id=id,version='1'), provenance=PROV)


def report():
    return c.ReportState(status='final', reported=time(), available=time())


def facts():
    specimen = m.Specimen(**base('S'), accession=code('accession'), specimen_type=concept('blood'), site=concept('recorded site'), collected=time(), received=time(AT+timedelta(minutes=10)), collector='recorded collector')
    isolate = m.IsolateIdentification(**base('I'), domain_bindings=(binding(),), report=report(), isolate_identifier=code('isolate-1'), organism=concept('same organism'), identification_state='provisional', identified=time())
    susceptibility = m.SusceptibilityResult(**base('U'), domain_bindings=(binding('isolate','I'),), report=report(), test_identifier=code('test-1'), antimicrobial=drug(), result_status='reported', mic=m.MinimumInhibitoryConcentration(comparator='<=',quantity=quantity('1.000')), interpretation=m.SusceptibilityInterpretation(raw=' I ', category='intermediate',coding=code('I','source.interpretation')), breakpoint=m.BreakpointContext(authority='recorded authority',version='source-v1'))
    administration = a.CompletedAntimicrobialAdministration(**base('D'), antimicrobial=drug(), administered_dose=a.RecordedDose(amount=quantity('500.00','mg'),basis='total_administered'), administered=time(), route=concept('recorded route'))
    order = a.AntimicrobialOrder(**base('O'), antimicrobial=drug(), order_status='active', prescribed_dose=a.RecordedDose(amount=quantity('500.00','mg'),basis='per_dose'), created=time())
    return specimen,isolate,susceptibility,administration,order


def all_facts():
    specimen,isolate,susceptibility,administration,order=facts()
    return (specimen,isolate,susceptibility,administration,order,
        m.DirectExamination(**base('E'),domain_bindings=(binding(),),report=report(),examination_type='gram_stain',findings=(m.ExaminationFinding(category='gram_reaction',finding=concept('negative'),presence='present'),)),
        m.CultureFinding(**base('C'),domain_bindings=(binding(),),report=report(),growth='no_growth'),
        m.ResistanceFinding(**base('R'),domain_bindings=(binding('isolate','I'),),report=report(),category='esbl',target=concept('reported ESBL'),result='positive'),
        m.MolecularResult(**base('P'),domain_bindings=(binding(),),report=report(),test_identifier=code('PCR'),panel_identifier=code('panel-1'),target=concept('target-1'),result='negative'),
        m.BloodCultureSet(**base('SET'),set_identifier=code('set-1'),collected=time()),
        m.BloodCultureBottle(**base('BOTTLE'),domain_bindings=(binding('collection_set','SET'),binding()),bottle_identifier=code('bottle-1'),bottle_type=concept('source bottle type'),bottle_role='aerobic',positive_at=time(),reported_time_to_positivity=quantity('12.00','h')),
        a.AntimicrobialNonDelivery(**base('N'),antimicrobial=drug(),status='held',occurred=time(),domain_bindings=(binding('order','O'),)))


def item(fact, **kw):
    return s.RetainedStateItemV2(fact=fact,expected_digest=fact.canonical_digest,inclusion=kw.pop('inclusion','in_window' if fact.semantic_time.anchor else 'unplaced'),disclosures=('supplied contract only; not persisted',),**kw)


def scope():
    return s.PatientStateScopeV2(patient_id='synthetic-p1',encounter_id='synthetic-e1',review_start=AT,review_end=AT+timedelta(hours=2),repository_cutoff=RepositoryCutoff(repository_id=REPO,fact_watermark=100,captured_at=AT+timedelta(days=1)))


def snapshot(records=None, **kw):
    records = tuple(item(f) for f in facts()) if records is None else records
    micro=tuple(i.reference for i in records if i.fact.kind.startswith('microbiology') or i.fact.kind.startswith('blood_culture'))
    a_view=s.AntimicrobialView(orders=tuple(i.reference for i in records if i.fact.kind=='antimicrobial_order'),administrations=tuple(i.reference for i in records if i.fact.kind=='antimicrobial_administration'),non_delivery=tuple(i.reference for i in records if i.fact.kind=='antimicrobial_non_delivery'))
    return s.PatientStateSnapshotV2(scope=kw.pop('scope',scope()),items=records,microbiology=kw.pop('microbiology',s.MicrobiologyView(references=micro)),antimicrobial=kw.pop('antimicrobial',a_view),**kw)


@pytest.mark.parametrize('index',range(12))
def test_each_fact_frozen_roundtrip_and_explicit_admission(index):
    fact=all_facts()[index]
    encoded=canonical_payload(fact)
    assert canonical_payload(type(fact).model_validate_json(encoded))==encoded
    assert fact.canonical_digest==sha256(encoded.encode()).hexdigest()
    with pytest.raises(ValidationError): fact.id='changed'
    with pytest.raises(ValidationError): fact.provenance.actor='changed'
    assert canonical_payload(validate_fact(fact)) == encoded


@pytest.mark.parametrize('index',range(12))
def test_each_fact_rejects_inferred_origin_and_unknown_fields(index):
    fact=all_facts()[index]
    with pytest.raises(ValidationError): change(fact,origin='inferred')
    with pytest.raises(ValidationError): change(fact,metadata={'clinical':'escape hatch'})


@pytest.mark.parametrize('index',range(12))
def test_each_fact_correction_retains_exact_identity(index):
    fact=all_facts()[index]
    values=dict(revision='2',supersedes=fact.reference,correction_reason='same-value source correction')
    if hasattr(fact,'report'): values['report']=change(fact.report,change='corrected')
    newer=change(fact,**values)
    assert newer.id==fact.id and newer.reference.version=='2' and newer.supersedes==fact.reference
    assert newer.canonical_digest!=fact.canonical_digest
    with pytest.raises(ValidationError): change(newer,supersedes=Reference(kind=fact.kind,id='other',version='1'))


@pytest.mark.parametrize('status',['missing','unknown','not_recorded'])
def test_missing_time_is_not_fabricated(status):
    t=c.RecordedTime(status=status)
    assert t.anchor is None
    assert json.loads(canonical_payload(t))['value'] is None
    with pytest.raises(ValidationError): change(t,value=AT)


@pytest.mark.parametrize('comparator',['<','<=','=','>=','>'])
def test_mic_exact_comparator_scale_unit(comparator):
    mic=m.MinimumInhibitoryConcentration(comparator=comparator,quantity=quantity('0.00100'))
    value=json.loads(canonical_payload(mic))
    assert value['quantity']['value']=='0.00100'
    assert value['comparator']==comparator
    assert value['quantity']['unit']['raw']=='mg/L'


@pytest.mark.parametrize('value',[1.2,True,float('nan'),float('inf'),'-1'])
def test_invalid_mic_never_coerced(value):
    with pytest.raises(ValidationError): m.MinimumInhibitoryConcentration(comparator='=',quantity=quantity(value))


def test_specimen_distinct_roles_and_accession_namespace():
    specimen=facts()[0]
    assert specimen.collected.value.isoformat()=='2026-10-08T08:00:00.123456+05:30'
    assert specimen.received.value.isoformat()=='2026-10-08T08:10:00.123456+05:30'
    assert specimen.site.raw_display=='recorded site' and specimen.recorded_adequacy is None
    other=change(specimen,id='S2',accession=code('accession','other.lab'))
    assert other.accession!=specimen.accession
    # No universal chronology is invented across laboratory roles.
    assert change(specimen,received=time(AT-timedelta(days=1))).received.value < specimen.collected.value


def test_approximate_bounded_and_aware_time():
    approximate=c.RecordedTime(status='known',precision='approximate',value=AT,uncertainty='source approximation')
    assert approximate.uncertainty=='source approximation'
    bounded=c.RecordedTime(status='known',precision='bounded',lower=AT,upper=AT+timedelta(hours=1))
    assert bounded.value is None and bounded.anchor==AT
    with pytest.raises(ValidationError): change(bounded,upper=AT-timedelta(seconds=1))
    with pytest.raises(ValidationError): time(AT.replace(tzinfo=None))
    with pytest.raises(ValidationError): change(approximate,uncertainty=None)


def test_actual_instants_dst_and_representation():
    zone=ZoneInfo('America/New_York')
    first=datetime(2026,11,1,1,30,tzinfo=zone,fold=0)
    second=datetime(2026,11,1,1,30,tzinfo=zone,fold=1)
    assert c.instant(second)-c.instant(first)==3_600_000_000
    assert c.instant(AT)==c.instant(AT.astimezone(timezone.utc))
    assert '-04:00' in canonical_payload(time(first))
    assert '-05:00' in canonical_payload(time(second))


@pytest.mark.parametrize('growth',['growth','no_growth','indeterminate'])
def test_culture_explicit_result(growth):
    culture=change(all_facts()[6],growth=growth)
    assert json.loads(canonical_payload(culture))['growth']==growth
    if growth=='no_growth':
        with pytest.raises(ValidationError): change(culture,quantity=quantity('1'))


def test_organism_name_does_not_define_isolate():
    isolate=facts()[1]
    other=change(isolate,id='I2',isolate_identifier=code('isolate-2'))
    assert other.organism==isolate.organism and other.reference!=isolate.reference
    final=change(isolate,revision='2',supersedes=isolate.reference,correction_reason='source continuity',report=change(isolate.report,change='amended'),identification_state='final',organism=concept('Klebsiella pneumoniae'))
    assert final.isolate_identifier==isolate.isolate_identifier
    assert final.stable_identity==isolate.stable_identity


@pytest.mark.parametrize('status,disposition',[('pending','original'),('final','corrected'),('preliminary','amended'),('interim','original'),('withdrawn','superseded')])
def test_report_status_orthogonal(status,disposition):
    r=c.ReportState(status=status,change=disposition)
    assert r.status==status and r.change==disposition


def test_susceptibility_correction_and_raw_interpretation():
    old=facts()[2]
    new=change(old,revision='2',supersedes=old.reference,correction_reason='MIC amended',report=change(old.report,change='corrected'),mic=m.MinimumInhibitoryConcentration(comparator='>',quantity=quantity('2.00')),interpretation=m.SusceptibilityInterpretation(raw=' R ',category='resistant',coding=code('R','other.system')))
    assert old.mic.quantity.value==Decimal('1.000') and new.mic.quantity.value==Decimal('2.00')
    assert old.interpretation.raw==' I ' and old.breakpoint.version=='source-v1'
    assert new.domain_bindings==old.domain_bindings
    assert new.provenance.dependencies==()
    with pytest.raises(ValidationError): change(old,result_status='not_performed')


@pytest.mark.parametrize('result',['positive','negative','indeterminate','not_performed'])
def test_molecular_and_resistance_explicit_calls(result):
    molecular=change(all_facts()[8],result=result)
    resistance=change(all_facts()[7],result=result)
    assert molecular.result==resistance.result==result
    other=change(molecular,id='P2',target=concept('target-2'))
    assert other.reference!=molecular.reference and other.panel_identifier==molecular.panel_identifier


def test_binding_states_and_target_integrity():
    b=binding('isolate','I')
    assert b.exact.version=='1' and b.stable_target.id=='I'
    unresolved=change(b,status='unresolved',exact=None,limitation='not supplied')
    assert unresolved.status=='unresolved'
    refs=(b.exact,Reference(kind='microbiology_isolate',id='I2',version='1'))
    ambiguous=change(b,status='ambiguous',stable_target=None,exact=None,candidates=refs,limitation='two candidates')
    assert ambiguous.status=='ambiguous' and ambiguous.exact is None
    with pytest.raises(ValidationError): change(b,exact=Reference(kind='microbiology_isolate',id='wrong',version='1'))
    with pytest.raises(ValidationError): change(b,role='specimen')
    with pytest.raises(ValidationError): change(ambiguous,candidates=refs[:1])


def test_scope_mismatch_and_duplicate_roles_rejected():
    isolate=facts()[1]
    foreign=change(binding(),scope=ContextTarget(patient_id='other',encounter_id='other'))
    with pytest.raises(ValidationError): change(isolate,domain_bindings=(foreign,))
    with pytest.raises(ValidationError): change(isolate,domain_bindings=(binding(),binding()))
    with pytest.raises(ValidationError): change(isolate,domain_bindings=())


@pytest.mark.parametrize('status',['unknown','unsupported','ambiguous'])
def test_unknown_drug_mapping_does_not_assert_identity(status):
    identity=change(drug(),mapping_status=status,canonical_id=None,ingredient_ids=(),limitation='not mapped')
    assert identity.canonical_id is None and identity.raw_display==' Source DRUG '
    with pytest.raises(ValidationError): change(identity,canonical_id='guessed')


def test_order_intent_and_delivered_total_distinct():
    order=facts()[4]
    assert order.order_status=='active' and not hasattr(order,'administered_dose')
    admin=facts()[3]
    assert admin.completion=='completed' and admin.administered_dose.amount.value==Decimal('500.00')
    with pytest.raises(ValidationError): change(admin,administered_dose=change(admin.administered_dose,basis='per_dose'))
    assert change(admin,administered=c.RecordedTime(status='missing')).semantic_time.anchor is None


@pytest.mark.parametrize('value',['0','-1',0.5])
def test_delivery_amount_must_be_positive_exact(value):
    with pytest.raises(ValidationError): a.RecordedDose(amount=quantity(value),basis='total_administered')


@pytest.mark.parametrize('status',['held','refused','missed','cancelled','not_given'])
def test_non_delivery_is_separate(status):
    event=change(all_facts()[11],status=status)
    assert event.status==status and not hasattr(event,'administered_dose')
    with pytest.raises(ValidationError): change(event,administered_dose=quantity('0'))


@pytest.mark.parametrize('category',['empiric','targeted','prophylactic','definitive','suppression'])
def test_purpose_requires_explicit_source(category):
    p=a.DocumentedTherapyPurpose(category=category,source_wording='source purpose',provenance=PROV)
    assert change(facts()[4],therapy_purpose=p).therapy_purpose.category==category
    assert facts()[4].therapy_purpose is None


def test_blood_set_bottle_identity_and_positivity():
    bottle=all_facts()[10]
    assert bottle.bottle_identifier.code=='bottle-1'
    assert bottle.domain_bindings[0].exact.id=='SET'
    assert bottle.reported_time_to_positivity.value==Decimal('12.00')
    assert bottle.positive_at.value==AT
    assert all_facts()[1].domain_bindings[0].role=='specimen'


def test_snapshot_views_one_fact_multiple_views():
    snap=snapshot(medication_references=(facts()[3].reference,))
    assert len(snap.items)==5
    assert snap.medication_references[0]==snap.antimicrobial.administrations[0]
    assert len([i for i in snap.items if i.reference==snap.medication_references[0]])==1
    with pytest.raises(ValidationError): snap.items=()
    assert canonical_payload(s.PatientStateSnapshotV2.model_validate_json(canonical_payload(snap)))==canonical_payload(snap)


def test_item_order_independent_of_input_and_ingestion():
    records=tuple(item(f) for f in facts())
    left=snapshot(records)
    right=snapshot(tuple(reversed(records)),microbiology=left.microbiology,antimicrobial=left.antimicrobial)
    assert left.canonical_digest==right.canonical_digest
    assert [i.fact.id for i in left.items]==['D','O','I','S','U']


def test_missing_time_order_and_contextual_parent():
    specimen,isolate,susceptibility,admin,order=facts()
    missing=change(admin,administered=c.RecordedTime(status='missing'))
    records=tuple(item(f) for f in (specimen,isolate,susceptibility,missing,order))
    assert snapshot(records).items[-1].fact.id=='D'
    old=change(specimen,collected=time(AT-timedelta(days=2)))
    records=(item(old,inclusion='contextual_parent',contextual_for=(isolate.reference,)),)+tuple(item(f) for f in (isolate,susceptibility,admin,order))
    assert snapshot(records).items[0].fact.id=='S'
    with pytest.raises(ValidationError): item(old,inclusion='contextual_parent')


def test_duplicate_identity_scope_and_digest():
    records=tuple(item(f) for f in facts())
    with pytest.raises(ValidationError): snapshot(records+(records[0],))
    with pytest.raises(ValidationError): change(records[0],expected_digest='0'*64)
    with pytest.raises(ValidationError): snapshot(scope=change(scope(),patient_id='foreign'))
    old=facts()[0]
    newer=change(old,revision='2',supersedes=old.reference,correction_reason='source correction')
    with pytest.raises(ValidationError): snapshot(records+(item(newer),))


def test_ingestion_scope_prefix_and_duplicate_metadata():
    records=list(item(f) for f in facts())
    meta=IngestionMetadata(repository_id=REPO,ingestion_sequence=101,ingested_at=AT)
    records[0]=change(records[0],ingestion=meta)
    with pytest.raises(ValidationError): snapshot(tuple(records))
    with pytest.raises(ValidationError): snapshot(scope=change(scope(),repository_cutoff=RepositoryCutoff(repository_id=REPO,fact_watermark=0,captured_at=AT)),records=tuple(records))


def test_grouping_rejects_wrong_isolate():
    specimen,isolate,susceptibility,admin,order=facts()
    other=change(isolate,id='I2',isolate_identifier=code('isolate-2'))
    records=tuple(item(f) for f in (specimen,isolate,susceptibility,admin,order,other))
    view=snapshot(records).microbiology
    with pytest.raises(ValidationError): snapshot(records,microbiology=change(view,isolates=(s.IsolateGroup(isolate=other.reference,susceptibilities=(susceptibility.reference,)),)))
    good=change(view,isolates=(s.IsolateGroup(isolate=isolate.reference,susceptibilities=(susceptibility.reference,)),))
    assert snapshot(records,microbiology=good).microbiology.isolates[0].isolate==isolate.reference


def test_binding_absence_disclosed_not_silently_resolved():
    isolate=facts()[1]
    with pytest.raises(ValidationError): snapshot((item(isolate),))
    issue=s.MappingIssueV2(reference=isolate.reference,reason='binding_target_unavailable')
    assert snapshot((item(isolate),),issues=(issue,)).issues==(issue,)


@pytest.mark.parametrize('kind',['findings','bindings','susceptibilities','targets','items'])
def test_collection_overflow_rejected(kind):
    with pytest.raises(ValidationError):
        if kind=='findings': change(all_facts()[5],findings=all_facts()[5].findings*33)
        elif kind=='bindings': change(facts()[1],domain_bindings=(binding(),)*17)
        elif kind=='susceptibilities': s.IsolateGroup(isolate=facts()[1].reference,susceptibilities=(facts()[2].reference,)*65)
        elif kind=='targets': s.MolecularPanelGroup(panel=code('panel'),targets=(all_facts()[8].reference,)*65)
        else: s.PatientStateSnapshotV2(scope=scope(),items=(item(facts()[0]),)*513)


def test_mutation_through_input_alias_and_nested_objects():
    findings=[m.ExaminationFinding(category='gram_reaction',finding=concept('negative'),presence='present')]
    exam=change(all_facts()[5],findings=findings)
    findings.clear()
    assert len(exam.findings)==1
    with pytest.raises(ValidationError): exam.findings[0].finding.raw_display='changed'
    data=exam.model_dump(); data['findings'][0]['finding']['raw_display']='changed'
    assert exam.findings[0].finding.raw_display=='negative'


def test_coverage_incomplete_is_not_absence_or_corruption():
    unknown=s.CoverageV2(domain='microbiology',mapping_support='unsupported',retrieval='not_attempted',limitations=('source unsupported',))
    assert unknown.retained_count is None
    with pytest.raises(ValidationError): change(unknown,retained_count=0)
    limit=change(unknown,mapping_support='partial',retrieval='limit_exceeded')
    assert limit.source_completeness=='unknown'


def test_unknown_enum_and_bad_report_correction():
    with pytest.raises(ValidationError): c.ReportState(status='final_corrected')
    with pytest.raises(ValidationError): change(facts()[2],report=change(report(),change='corrected'))
    with pytest.raises(ValidationError): m.MinimumInhibitoryConcentration(comparator='approximately',quantity=quantity())


def test_view_order_is_canonical_independent_of_input_order():
    records=tuple(item(f) for f in facts())
    left=snapshot(records)
    right=snapshot(tuple(reversed(records)))
    assert left.canonical_digest==right.canonical_digest
    assert canonical_payload(s.MicrobiologyView(references=tuple(reversed(left.microbiology.references))))==canonical_payload(left.microbiology)


def test_standalone_view_duplicates_rejected():
    ref=facts()[2].reference
    with pytest.raises(ValidationError): s.IsolateGroup(isolate=facts()[1].reference,susceptibilities=(ref,ref))
    with pytest.raises(ValidationError): s.MicrobiologyView(references=(ref,ref))


def test_panel_identity_is_structured_and_versioned():
    specimen=facts()[0]
    target=all_facts()[8]
    view=s.MicrobiologyView(references=(specimen.reference,target.reference),panels=(s.MolecularPanelGroup(panel=target.panel_identifier,targets=(target.reference,)),))
    assert snapshot((item(specimen),item(target)),microbiology=view).microbiology.panels[0].panel.version=='v1'
    wrong=change(view,panels=(s.MolecularPanelGroup(panel=change(target.panel_identifier,version='v2'),targets=(target.reference,)),))
    with pytest.raises(ValidationError): snapshot((item(specimen),item(target)),microbiology=wrong)


@pytest.mark.parametrize('owner',['fact','binding','mapping','purpose'])
def test_all_provenance_collections_bounded(owner):
    oversized={**PROV.model_dump(),'limitations':('source limitation',)*33}
    with pytest.raises(ValidationError):
        if owner=='fact': change(facts()[0],provenance=oversized)
        elif owner=='binding': change(binding(),provenance=oversized)
        elif owner=='mapping': change(drug(),mapping_provenance=oversized)
        else: a.DocumentedTherapyPurpose(category='empiric',source_wording='recorded',provenance=oversized)


def test_common_event_cannot_compete_with_typed_time():
    with pytest.raises(ValidationError): change(facts()[0],time=ClinicalTime(event=AT,precision='instant'))


def test_unsupported_coverage_cannot_hide_retained_items():
    coverage=s.CoverageV2(domain='microbiology',mapping_support='unsupported',retrieval='not_attempted',limitations=('not mapped',))
    with pytest.raises(ValidationError): snapshot(coverage=(coverage,))


def test_bottle_binding_cannot_contradict_specimen_binding():
    all_records=all_facts()
    second=change(all_records[0],id='S2',accession=code('accession-2'))
    isolate=change(all_records[1],domain_bindings=(binding(),binding('bottle','BOTTLE')))
    bottle=change(all_records[10],domain_bindings=(binding('collection_set','SET'),binding(id='S2')))
    records=(all_records[0],second,isolate,all_records[9],bottle)
    with pytest.raises(ValidationError): snapshot(tuple(item(f) for f in records))


def test_reassignment_requires_new_exact_revision_and_preserves_old_binding():
    old=facts()[2]
    new=change(old,revision='2',supersedes=old.reference,correction_reason='explicit isolate reassignment',report=change(report(),change='corrected'),domain_bindings=(binding('isolate','I2'),))
    assert old.domain_bindings[0].exact.id=='I'
    assert new.domain_bindings[0].exact.id=='I2'
    assert new.supersedes==old.reference


def test_provenance_only_correction_changes_digest():
    old=facts()[0]
    new=change(old,revision='2',supersedes=old.reference,correction_reason='source author correction',provenance=change(old.provenance,actor='corrected source author'))
    assert new.collected==old.collected and new.canonical_digest!=old.canonical_digest


def test_order_details_and_infusion_are_recorded_only():
    order=facts()[4]
    order=change(order,frequency=a.RecordedFrequency(occurrences=2,interval=quantity('24.00','h')),schedule='source schedule',scheduling='prn',recorded_indication='explicit indication',intended_start=time(),intended_end=time(AT+timedelta(days=1)),discontinued=time(AT+timedelta(hours=4)),discontinuation_reason='source reason')
    assert order.frequency.interval.value.as_tuple().exponent==-2
    with pytest.raises(ValidationError): change(order,intended_end=time(AT-timedelta(seconds=1)))
    admin=facts()[3]
    admin=change(admin,infusion_start=time(),infusion_end=time(AT+timedelta(hours=1)),administered_dose=change(admin.administered_dose,rate=quantity('500.00','mg/h'),duration=quantity('1.00','h')))
    assert admin.administered_dose.duration.value==Decimal('1.00')
    with pytest.raises(ValidationError): change(admin,infusion_end=time(AT-timedelta(seconds=1)))


def test_independent_antimicrobial_source_codes_not_name_matching():
    first=drug()
    second=change(first,source_code=code('drug-2'),mapping_status='unknown',canonical_id=None,ingredient_ids=(),limitation='no equivalence assertion')
    assert first.raw_display==second.raw_display and first.source_code!=second.source_code
    assert second.canonical_id is None


def test_zone_and_missing_breakpoint_version_preserved():
    result=change(facts()[2],mic=None,zone_diameter=quantity('12.00','mm'),breakpoint=m.BreakpointContext(authority='source authority'))
    assert json.loads(canonical_payload(result))['zone_diameter']['value']=='12.00'
    assert result.breakpoint.version is None


def test_all_instantiated_nested_models_frozen():
    from pydantic import BaseModel
    seen=set()
    def visit(value):
        if isinstance(value,BaseModel):
            seen.add(type(value))
            for name in type(value).model_fields:
                field=getattr(value,name)
                with pytest.raises(ValidationError): setattr(value,name,field)
                visit(field)
        elif isinstance(value,(tuple,list)):
            for child in value: visit(child)
    for fact in all_facts(): visit(fact)
    visit(snapshot())
    visit(s.SpecimenGroup(specimen=facts()[0].reference))
    visit(s.IsolateGroup(isolate=facts()[1].reference))
    visit(s.MolecularPanelGroup(panel=code('panel'),targets=(all_facts()[8].reference,)))
    visit(a.DocumentedTherapyPurpose(category='empiric',source_wording='source',provenance=PROV))
    visit(a.RecordedFrequency(occurrences=1,interval=quantity('1','h')))
    visit(s.MappingIssueV2(reference=facts()[0].reference,reason='missing_collection_time'))
    visit(s.CoverageV2(domain='microbiology',mapping_support='unsupported',retrieval='not_attempted',limitations=('unknown',)))
    assert len(seen)>=35


def test_unvalidated_copies_rechecked_at_composition():
    bad=facts()[0].model_copy(update={'origin':'inferred'})
    with pytest.raises(ValidationError): item(bad)
    bad_meta=IngestionMetadata(repository_id=REPO,ingestion_sequence=1,ingested_at=AT).model_copy(update={'ingestion_sequence':0})
    with pytest.raises(ValidationError): item(facts()[0],ingestion=bad_meta)


def test_clinical_order_ignores_ingestion_sequence():
    records=list(item(f) for f in facts())
    earlier=change(facts()[3],administered=time(AT+timedelta(minutes=5)))
    later=change(facts()[4],created=time(AT+timedelta(minutes=10)))
    records[3]=item(earlier,ingestion=IngestionMetadata(repository_id=REPO,ingestion_sequence=99,ingested_at=AT))
    records[4]=item(later,ingestion=IngestionMetadata(repository_id=REPO,ingestion_sequence=1,ingested_at=AT))
    result=snapshot(tuple(records))
    assert [i.fact.id for i in result.items][-2:]==['D','O']


def test_missing_collection_and_ambiguous_binding_are_valid_incomplete_data():
    specimen=change(facts()[0],collected=c.RecordedTime(status='missing'))
    b=binding()
    b=change(b,status='ambiguous',stable_target=None,exact=None,candidates=(b.exact,Reference(kind='microbiology_specimen',id='S2',version='1')),limitation='ambiguous source linkage')
    isolate=change(facts()[1],domain_bindings=(b,))
    value=snapshot((item(specimen),item(isolate)))
    assert value.items[-1].fact.id=='S'
    assert isolate.domain_bindings[0].status=='ambiguous'


def test_closed_window_boundaries_and_contextual_link_validation():
    at_end=change(facts()[0],collected=time(AT+timedelta(hours=2)))
    assert snapshot((item(at_end),)).items[0].fact.collected.value==AT+timedelta(hours=2)
    with pytest.raises(ValidationError): snapshot((item(change(at_end,collected=time(AT+timedelta(hours=2,microseconds=1)))),))
    unrelated=Reference(kind='microbiology_isolate',id='missing',version='1')
    with pytest.raises(ValidationError): snapshot((item(facts()[0],inclusion='contextual_parent',contextual_for=(unrelated,)),))


def test_explicit_persistence_admission_does_not_expand_governance_fact_union():
    from app.persistence.mapping import SUPPORTED_FACTS
    from app.persistence.history import FactIdentity
    assert {'observation','medication_order','medication_administration','inference'} <= set(SUPPORTED_FACTS)
    assert FactIdentity(kind='microbiology_specimen',id='S').kind == 'microbiology_specimen'
    from app.models.clinical.facts import Fact
    from pydantic import TypeAdapter
    with pytest.raises(ValidationError): TypeAdapter(Fact).validate_python(facts()[0].model_dump())
    with pytest.raises(ValidationError): FactIdentity(kind='unadmitted',id='S')


@pytest.mark.parametrize('owner', ['fact', 'binding', 'mapping', 'purpose'])
@pytest.mark.parametrize('collection', ['upstream', 'limitations', 'basis'])
def test_provenance_exact_bounds_roundtrip_and_aliases(owner, collection):
    def build(payload):
        if owner == 'fact': return change(facts()[0], provenance=payload)
        if owner == 'binding': return change(binding(), provenance=payload)
        if owner == 'mapping': return change(drug(), mapping_provenance=payload)
        return a.DocumentedTherapyPurpose(category='empiric', source_wording='recorded', provenance=payload)
    def edge(index):
        return dict(target=Reference(kind='observation', id=f'e{index}', version='1'), relationship='copied_from')
    values = [f'limit-{n}' for n in range(32)] if collection == 'limitations' else [edge(n) for n in range(32)]
    payload = PROV.model_dump()
    if collection == 'basis':
        values = [Reference(kind='observation', id=f'b{n}', version='1') for n in range(16)]
        payload['upstream'] = [dict(target=Reference(kind='inference', id='inference', version='1'), relationship='independent_confirmation', basis=values, rationale='recorded independent basis')]
    else:
        payload[collection] = values
    value = build(payload)
    encoded = canonical_payload(value)
    assert canonical_payload(type(value).model_validate_json(encoded)) == encoded
    provenance = value.mapping_provenance if owner == 'mapping' else value.provenance
    retained = provenance.upstream[0].basis if collection == 'basis' else getattr(provenance, collection)
    assert isinstance(retained, tuple)
    assert len(retained) == (16 if collection == 'basis' else 32)
    values.append(Reference(kind='observation', id='overflow', version='1') if collection == 'basis' else 'overflow' if collection == 'limitations' else edge(32))
    assert canonical_payload(value) == encoded
    with pytest.raises(ValidationError): build(payload)
    values.clear()
    assert canonical_payload(value) == encoded


@pytest.mark.parametrize('model,field,parent', [
    (s.SpecimenGroup, 'examinations', 'specimen'),
    (s.SpecimenGroup, 'cultures', 'specimen'),
    (s.SpecimenGroup, 'isolates', 'specimen'),
    (s.SpecimenGroup, 'molecular_results', 'specimen'),
    (s.IsolateGroup, 'susceptibilities', 'isolate'),
    (s.IsolateGroup, 'resistance_findings', 'isolate'),
    (s.MolecularPanelGroup, 'targets', 'panel'),
    (s.AntimicrobialView, 'orders', None),
    (s.AntimicrobialView, 'administrations', None),
    (s.AntimicrobialView, 'non_delivery', None),
])
def test_each_view_role_order_and_input_alias(model, field, parent):
    refs = [Reference(kind='observation', id=name, version='1') for name in ('z', 'a')]
    kwargs = {} if parent is None else {parent: code('panel') if parent == 'panel' else facts()[0].reference}
    value = model(**kwargs, **{field: refs})
    other = model(**kwargs, **{field: list(reversed(refs))})
    assert value.canonical_digest == other.canonical_digest
    assert [r.id for r in getattr(value, field)] == ['a', 'z']
    assert [r.id for r in refs] == ['z', 'a']
    encoded = canonical_payload(value)
    refs.clear()
    assert canonical_payload(value) == encoded
    with pytest.raises(ValidationError): model(**kwargs, **{field: [getattr(value, field)[0]] * 2})


def test_nested_view_group_permutations_preserve_roles():
    def ref(kind, name): return Reference(kind=kind, id=name, version='1')
    groups = dict(
        specimens=[s.SpecimenGroup(specimen=ref('microbiology_specimen', n)) for n in ('z','a')],
        isolates=[s.IsolateGroup(isolate=ref('microbiology_isolate', n)) for n in ('z','a')],
        panels=[s.MolecularPanelGroup(panel=code(n), targets=(ref('microbiology_molecular_result', n),)) for n in ('z','a')],
    )
    left = s.MicrobiologyView(**groups)
    right = s.MicrobiologyView(**{k:list(reversed(v)) for k,v in groups.items()})
    assert left.canonical_digest == right.canonical_digest
    assert groups['specimens'][0].specimen.id == 'z'
    assert left.specimens[0].specimen.kind != left.isolates[0].isolate.kind
    for field, values in groups.items():
        with pytest.raises(ValidationError): s.MicrobiologyView(**{field:[values[0],values[0]]})


def test_missing_time_permutations_and_role_distinction():
    records = [item(change(facts()[0], id=name, collected=c.missing_time())) for name in ('z','a')]
    first = snapshot(records)
    second = snapshot(list(reversed(records)))
    assert first.canonical_digest == second.canonical_digest
    assert [i.fact.id for i in first.items] == ['a','z']
    assert [i.fact.id for i in records] == ['z','a']
    ref = facts()[4].reference
    assert s.AntimicrobialView(orders=(ref,)).canonical_digest != s.AntimicrobialView(administrations=(ref,)).canonical_digest
