"""Synthetic recorded evidence, not clinical diagnoses or treatment expectations."""
from datetime import timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from uuid import UUID
import pytest
from pydantic import ValidationError, TypeAdapter
from app.models.clinical import hemodynamics as h
from app.models.clinical.recorded_v2 import RecordedConcept, SourceCode
from app.persistence.canonical import canonical_payload
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff
from app.execution import patient_state_v3 as s
from test_patient_state_v2 import AT, TARGET, PROV, base, change, time, quantity


def code(value='source'):
    return SourceCode(namespace='synthetic.m7', code=value, version='1', raw_display=value)


def concept(value='source description'):
    return RecordedConcept(raw_display=value)


def stamp(at=AT):
    return h.ClinicalInstant(recorded=time(at), source_timestamp=at.isoformat(), timestamp_precision=h.PRECISION_CONTRACT, clock='verified', clock_basis=PROV)


def acquisition(method='invasive_arterial', **kw):
    fields = dict(method=method, calibration='adequate', zeroing='adequate',
        calibration_provenance=PROV, zeroing_provenance=PROV,
        quality=h.EvidenceQuality(status='acceptable', provenance=PROV))
    fields.update(kw)
    return h.Acquisition(**fields)


def numeric(value='65.00', unit='mmHg'):
    return h.NumericResult(quantity=quantity(value, unit))


def measurement(cls=h.PressureObservation, name='p', **kw):
    fields = dict(base(name), occurred=stamp(), available=stamp(),
        result=numeric(), acquisition=acquisition(), production='direct_measurement')
    fields.update(kw)
    if cls is h.PressureObservation:
        fields.setdefault('concept', 'systemic_mean')
    return cls(**fields)


def device(technology='PiCCO', platform='PiCCO'):
    return h.DeviceIdentity(manufacturer=code('manufacturer'), platform=platform,
        product=code('product'), technology=technology, sensor=code('sensor'))


def drug():
    return h.VasoactiveIdentity(source=code('norepinephrine'), canonical_id='norepinephrine',
        mapping='mapped', mapping_provenance=PROV)


def vaso(action='initiation'):
    payload = ({'event_type': action, 'delivery': {'attestation': PROV}}
        if action in ('initiation', 'rate_change', 'restart', 'bolus') else
        {'event_type': 'order', 'prescribed': {}, 'status': concept()} if action == 'order' else
        {'event_type': 'preparation', 'prepared': {}} if action == 'preparation' else
        {'event_type': action, 'reason': concept()})
    return h.VasoactiveEvent(**base('v-'+action), occurred=stamp(), available=stamp(),
        drug=drug(), action=payload, source_status=concept('documented'))


def records():
    return (
        measurement(),
        measurement(h.CardiacPerformance, 'co', concept='co'),
        measurement(h.VolumeMeasurement, 'gedv', concept='gedv'),
        measurement(h.DynamicMeasurement, 'svv', concept='svv'),
        measurement(h.DevicePrediction, 'hpi', acquisition=acquisition(device=device('AcumenIQ', 'HemoSphere'),
            parameter=code('HPI')), production='monitor_derived'),
        measurement(h.PerfusionObservation, 'crt', concept='capillary_refill'),
        measurement(h.OxygenTransport, 'sv', concept='svo2', sample_type='mixed_venous'),
        measurement(h.LactateResult, 'l', collected=stamp(), collection_assertion=PROV,
            result=numeric('2.00', 'mmol/L'), specimen=code('sample'), report_status='final'),
        measurement(h.EchoObservation, 'echo', concept='tapse', study=code('study'),
            report=code('report'), report_revision='1'),
        measurement(h.ECGObservation, 'ecg', concept='qtc', interpretation_source='clinician'),
        vaso(),
        h.MonitoringEvent(**base('cal'), occurred=stamp(), device=device(),
            event_type='calibration', acquisition=acquisition(), finding=concept()),
        h.DynamicAssessment(**base('test'), occurred=stamp(), test='plr', protocol=code('plr'),
            baseline=(), intervention=(), subsequent=()),
        h.CirculatoryEvent(**base('surgery'), occurred=stamp(), event_type='transplantation',
            description=concept('recorded surgery')),
        h.SignalManifest(**base('signal'), occurred=stamp(), signal='arterial_pressure',
            device=device(), channel=code(), start=stamp(), end=stamp(AT+timedelta(seconds=1)),
            sample_rate=quantity('125', 'Hz'), sample_count=125, units=concept('mmHg'),
            encoding=code('source-encoding'), availability='unavailable'),
    )


@pytest.mark.parametrize('index', range(15))
def test_record_roundtrip_freeze_and_exact_values(index):
    fact = records()[index]
    payload = canonical_payload(fact)
    restored = TypeAdapter(h.CirculatoryRecord).validate_json(payload)
    assert type(restored) is type(fact)
    assert canonical_payload(restored) == payload
    assert fact.canonical_digest == sha256(payload.encode()).hexdigest()
    assert restored.reference.kind == fact.kind
    with pytest.raises(ValidationError):
        restored.provenance.actor = 'changed'
    with pytest.raises(ValidationError):
        restored.id = 'changed'


@pytest.mark.parametrize('action', ['order','preparation','initiation','rate_change','pause',
                                   'restart','permanent_stop','bolus','non_delivery'])
def test_event_variants_remain_distinct(action):
    fact = vaso(action)
    assert fact.action.event_type == action
    if action in ('pause', 'permanent_stop', 'non_delivery'):
        with pytest.raises(ValidationError):
            change(fact.action, delivery={})


@pytest.mark.parametrize('value', [1.5, True, 'NaN', 'Infinity', '-Infinity'])
def test_invalid_quantities_rejected(value):
    with pytest.raises(ValidationError):
        numeric(value)


def test_decimal_offset_and_signed_pressure_preserved():
    p = measurement(result=numeric('-2.00'), concept='cvp')
    payload = canonical_payload(p)
    assert '"value":"-2.00"' in payload
    assert AT.isoformat() in payload
    assert p.result.quantity.value == Decimal('-2.00')


@pytest.mark.parametrize('model,concepts', [
    (h.PressureObservation, ['systemic_systolic','systemic_diastolic','systemic_mean','cvp','rap','pasp','padp','mpap','pawp','lvedp']),
    (h.VolumeMeasurement, ['gedv','gedvi','itbv','itbvi','evlw','evlwi','pvpi','gef','cfi']),
    (h.CardiacPerformance, ['co','ci','sv','svi','cpo','cpi','svr','svri','pvr','pvri','tpg','dpg']),
    (h.DynamicMeasurement, ['ppv','svv','dynamic_arterial_elastance','dp_dt']),
])
def test_requested_metrics_are_independent_records(model, concepts):
    facts = [measurement(model, str(i), concept=c) for i,c in enumerate(concepts)]
    assert [f.concept for f in facts] == concepts
    assert len({f.reference for f in facts}) == len(concepts)


def test_source_derivation_is_not_clinrx_calculation():
    p = measurement(production='monitor_derived')
    assert p.production == 'monitor_derived'
    with pytest.raises(ValidationError):
        change(p, production='clinrx_calculated')
    with pytest.raises(ValidationError):
        change(p, calculation_inputs=[p.reference])


def test_source_configuration_does_not_invent_parameter_support():
    a = acquisition(method='pulse_contour', device=device('FloTrac','HemoSphere'))
    assert a.parameter_support == 'unknown'
    assert a.device.software is None
    assert change(a, device=device()).device.technology == 'PiCCO'
    with pytest.raises(ValidationError):
        measurement(h.DevicePrediction, 'hpi', acquisition=a, production='monitor_derived')


def test_clock_missing_quality_and_equivalent_offsets():
    assert not h.ClinicalInstant(recorded=time()).trustworthy
    assert h.EvidenceQuality().status == 'unknown'
    assert change(stamp(), conflicting=(AT.astimezone(timezone.utc),)).trustworthy
    assert not change(stamp(), conflicting=(AT+timedelta(seconds=1),)).trustworthy
    assert not change(stamp(), clock='unreliable').trustworthy
    assert not change(stamp(), recorded=change(time(), precision='approximate', uncertainty='source estimate')).trustworthy


@pytest.mark.parametrize('concept,sample', [('scvo2','mixed_venous'),('svo2','central_venous'),('spo2','arterial')])
def test_oxygen_sample_mismatch(concept,sample):
    with pytest.raises(ValidationError):
        measurement(h.OxygenTransport,'oxygen',concept=concept,sample_type=sample)


def test_caller_aliases_are_immutable():
    flags = ['recorded artifact']
    a = acquisition(quality=h.EvidenceQuality(artifacts=flags))
    flags.append('later')
    assert a.quality.artifacts == ('recorded artifact',)
    with pytest.raises(ValidationError):
        change(a, calibration_provenance=None)


def state(facts=None):
    facts = records() if facts is None else facts
    repo = UUID('00000000-0000-4000-8000-000000000001')
    scope = s.PatientStateScopeV3(patient_id=TARGET.patient_id,encounter_id=TARGET.encounter_id,
        review_start=AT, review_end=AT, repository_cutoff=RepositoryCutoff(repository_id=repo,
            fact_watermark=100,captured_at=AT))
    items = tuple(s.RetainedStateItemV3(fact=f,expected_digest=f.canonical_digest,
        ingestion=IngestionMetadata(repository_id=repo,ingestion_sequence=i+1,ingested_at=AT),
        inclusion='in_window',disclosures=('Synthetic recorded evidence only.',)) for i,f in enumerate(facts))
    return s.PatientStateSnapshotV3(scope=scope, items=items,
        coverage=s.CoverageV3(candidate_rows=len(items),terminal_count=len(items),retained_count=len(items)))


def test_state_order_scope_digest_and_no_reasoning():
    view = state()
    assert view.canonical_digest == change(view, items=tuple(reversed(view.items))).canonical_digest
    assert [i.reference for i in view.items] == sorted([f.reference for f in records()], key=lambda r:(r.kind,r.id,r.version))
    assert view.coverage.source_completeness == 'unknown'
    assert view.coverage.continuity == 'not_established'
    with pytest.raises(ValidationError): change(view, diagnosis='shock')
    with pytest.raises(ValidationError): change(view.items[0], expected_digest='0'*64)
    with pytest.raises(ValidationError): change(view, items=(view.items[0],view.items[0]))
    other = change(view.scope, encounter_id='foreign')
    with pytest.raises(ValidationError): change(view, scope=other)


def test_ordering_uses_actual_instants_not_offsets_or_revision_labels():
    p = measurement()
    q = measurement(name='q', occurred=stamp(AT.astimezone(timezone.utc)+timedelta(seconds=1)))
    scope = change(state((p,)).scope, review_end=AT+timedelta(seconds=2))
    original = state((p,)).items[0]
    qitem = change(original, fact=q, expected_digest=q.canonical_digest)
    view = s.PatientStateSnapshotV3(scope=scope,items=(qitem,original),
        coverage=s.CoverageV3(candidate_rows=2,terminal_count=2,retained_count=2))
    assert tuple(i.reference.id for i in view.items) == ('p','q')


def test_record_contract_rejects_competing_time_and_scope():
    p = measurement()
    with pytest.raises(ValidationError): change(p,time=change(p.time,event=AT))
    with pytest.raises(ValidationError): change(p, invented_threshold='shock')
    with pytest.raises(ValidationError): change(p, result={'result_type':'numeric','quantity':quantity('1'),'diagnosis':'shock'})


def test_source_timestamp_string_retained_without_utc_normalization():
    raw='2026-10-08T08:00:00.000+0530'
    t=h.ClinicalInstant(recorded={'status':'known','precision':'instant','value':raw},clock='verified',clock_basis=PROV)
    assert t.source_timestamp==raw
    assert t.recorded.value.isoformat()=='2026-10-08T08:00:00+05:30'
    assert raw in canonical_payload(t)
    with pytest.raises(ValidationError):change(t,source_timestamp='2026-10-08T08:00:00+00:00')


def test_clock_alignment_is_retained_without_adjusting_event_time():
    alignment=h.ClockAlignment(source_clock=code('monitor-clock'),reference_clock=code('reference-clock'),
        synchronization='unsynchronized',offset=quantity('1.250','s'),provenance=PROV)
    t=change(stamp(),alignment=alignment)
    assert not t.trustworthy
    assert t.recorded.value.isoformat()==AT.isoformat()
    assert str(t.alignment.offset.value)=='1.250'


def test_alternative_time_sources_keep_provenance_and_conflict():
    a=h.SourceTimeAssertion(recorded=time(AT+timedelta(seconds=1)),source=code('other-clock'),clock='verified',provenance=PROV)
    assert not change(stamp(),alternative_sources=(a,)).trustworthy
    b=change(a,recorded=time(AT.astimezone(timezone.utc)),source_timestamp=AT.astimezone(timezone.utc).isoformat(),timestamp_precision=h.PRECISION_CONTRACT)
    assert change(stamp(),alternative_sources=(b,)).trustworthy


def test_unavailable_signal_does_not_fabricate_sample_count_or_frequency():
    f=change(records()[-1],sample_count=None,sample_rate=None)
    assert f.availability=='unavailable' and f.sample_count is None and f.sample_rate is None
    assert f.content is None and f.content_sha256 is None


def test_known_clock_skew_never_becomes_exact_ordering_by_label_alone():
    alignment=h.ClockAlignment(source_clock=code(),synchronization='synchronized',offset=quantity('0.001','s'),provenance=PROV)
    assert not change(stamp(),alignment=alignment).trustworthy
    assert change(stamp(),alignment=change(alignment,offset=quantity('0.000','s'))).trustworthy
