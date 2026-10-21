"""M7 recorded circulatory evidence. No calculation, diagnosis or treatment policy.

Acquisition and mapping assertions are source evidence, never a claim that all
parameters are supported by every product/software/sensor configuration.
"""
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, Context
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, TypeAdapter, ValidationInfo, model_validator
from .common import ContextTarget, Reference, Text
from .facts import PatientFact
from .recorded_v2 import (Contract, RecordedTime, SourceCode, RecordedConcept,
    ExactQuantity, BoundedProvenance, instant, missing_time)

Notes = Annotated[tuple[Text, ...], Field(max_length=32)]
Refs = Annotated[tuple[Reference, ...], Field(max_length=32)]


class ClockAlignment(Contract):
    source_clock: SourceCode
    reference_clock: SourceCode | None = None
    synchronization: Literal['synchronized', 'unsynchronized', 'unknown']
    offset: ExactQuantity | None = None
    drift: ExactQuantity | None = None
    uncertainty: ExactQuantity | None = None
    assessed: RecordedTime = Field(default_factory=missing_time)
    provenance: BoundedProvenance


def _lossless_microseconds(value):
    """Datetime retains six fractional digits; discarded zeroes are harmless."""
    if value is None:
        return False
    try:
        raw = Decimal(value, context=Context(traps=[InvalidOperation]))
    except InvalidOperation:
        # Non-numeric source text must be an admitted ISO timestamp. If an
        # extreme numeric token cannot be represented exactly, abstain.
        if not re.match(r'^\d{4}-\d{2}-\d{2}[Tt _]', value):
            return False
    else:
        if not raw.is_finite():
            return False
        parsed = TypeAdapter(AwareDatetime).validate_python(value)
        epoch_us = instant(parsed) - instant(datetime(1970, 1, 1, tzinfo=timezone.utc))
        # Decimal constructors and comparisons are exact without expanding huge
        # exponents or depending on the caller's arithmetic precision context.
        return raw == Decimal(f'{epoch_us}e-6') or raw == Decimal(f'{epoch_us}e-3')
    fraction = re.search(r"[.,](\d+)", value)
    return fraction is None or not any(d != '0' for d in fraction.group(1)[6:])


def _numeric_time_lexeme(value):
    raw = str(value)
    if 'e' in raw.lower() and '.' not in raw:
        mantissa, exponent = re.split('[eE]', raw)
        return mantissa + '.0e' + exponent
    return raw


PRECISION_CONTRACT = 'M7ExactTimestampInput/v1'


def _source_lexeme(value):
    if isinstance(value, float):
        raise ValueError('M7 timestamps require exact text, integer, Decimal or datetime; float is not precision evidence')
    if isinstance(value, bool):
        raise ValueError('boolean is not timestamp evidence')
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError('invalid timestamp byte encoding') from None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, Decimal)):
        return _numeric_time_lexeme(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _exact_source(value, contract):
    return (_lossless_microseconds(value) and
        (contract == PRECISION_CONTRACT or bool(re.match(r'^\d{4}-\d{2}-\d{2}[Tt _]', value))))


def _retain_time(value):
    if isinstance(value, dict):
        recorded = value.get('recorded')
        if isinstance(recorded, dict):
            for anchor in ('value', 'lower', 'upper'):
                if isinstance(recorded.get(anchor), float):
                    raise ValueError('floating-point timestamp input cannot establish source precision')
            raw = _source_lexeme(recorded.get('value'))
            if raw is not None:
                if not _lossless_microseconds(raw):
                    if value.get('source_timestamp') not in (None, raw):
                        raise ValueError('source timestamp contradicts supplied fractional precision')
                    return {**value, 'source_timestamp': raw}
                if 'source_timestamp' not in value:
                    return {**value, 'source_timestamp': raw}
    return value


class SourceTimeAssertion(Contract):
    timestamp_precision: Literal['M7ExactTimestampInput/v1'] | None = Field(default=None, exclude_if=lambda v: v is None)
    source_timestamp: Annotated[str, Field(min_length=1, max_length=128)] | None = Field(default=None, exclude_if=lambda v: v is None)
    recorded: RecordedTime
    source: SourceCode
    clock: Literal['verified', 'unreliable', 'unknown'] = 'unknown'
    provenance: BoundedProvenance


    @model_validator(mode='before')
    @classmethod
    def retain_timestamp(cls, value, info: ValidationInfo):
        # A full previously serialized RecordedTime is not new source evidence.
        # Never infer a precision declaration when decoding/revalidating history.
        if isinstance(value, dict):
            recorded = value.get('recorded')
            if isinstance(recorded, dict):
                for anchor in ('value','lower','upper'):
                    if isinstance(recorded.get(anchor), float):
                        raise ValueError('floating-point timestamp input cannot establish source precision')
                if ('source_timestamp' not in value and 'timestamp_precision' not in value
                        and set(RecordedTime.model_fields) <= set(recorded)
                        and isinstance(recorded.get('value'), (str, datetime, type(None)))
                        and not (isinstance(recorded.get('value'), (str,bytes))
                            and not _lossless_microseconds(_source_lexeme(recorded['value'])))):
                    return value
        return _retain_time(value)

    @model_validator(mode='after')
    def consistent_timestamp(self):
        if self.timestamp_precision is not None and self.source_timestamp is None:
            raise ValueError('precision contract requires retained source timestamp')
        if self.source_timestamp is not None:
            parsed = TypeAdapter(AwareDatetime).validate_python(self.source_timestamp)
            if self.recorded.value is None or parsed.isoformat() != self.recorded.value.isoformat():
                raise ValueError('source timestamp contradicts alternative clinical time')
        return self


_CONFLICT_SHAPE = TypeAdapter(Annotated[tuple[object, ...], Field(max_length=8)])
_CONFLICT_TIMES = TypeAdapter(Annotated[tuple[AwareDatetime, ...], Field(max_length=8)])
_CONFLICT_LEXEMES = TypeAdapter(Annotated[tuple[str, ...], Field(max_length=8)])


def _conflict_lexeme(value, parsed):
    text = _source_lexeme(value)
    return parsed.isoformat() if text is None else text


class ClinicalInstant(Contract):
    timestamp_precision: Literal['M7ExactTimestampInput/v1'] | None = Field(default=None, exclude_if=lambda v: v is None)
    recorded: RecordedTime = Field(default_factory=missing_time)
    source_timestamp: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    clock: Literal['verified', 'unreliable', 'unknown'] = 'unknown'
    clock_basis: BoundedProvenance | None = None
    conflicting: Annotated[tuple[AwareDatetime, ...], Field(max_length=8)] = ()
    alternative_sources: Annotated[tuple[SourceTimeAssertion, ...], Field(max_length=8)] = ()
    alignment: ClockAlignment | None = None
    # Omitted for legacy payloads; retain lexemes only when actually supplied.
    conflicting_source_timestamps: Annotated[tuple[str, ...], Field(max_length=8, exclude_if=lambda v: not v)] = ()

    @model_validator(mode='before')
    @classmethod
    def retain_timestamp_lexeme(cls, value, info: ValidationInfo):
        value = _retain_time(value)
        if isinstance(value, dict):
            # Shape and datetime validation precede iteration/lexeme capture.
            # Materialize supported iterables only once, under the field's cap.
            conflicts = _CONFLICT_SHAPE.validate_python(value.get('conflicting', ()))
            for member in conflicts:
                _source_lexeme(member)  # reject floats before datetime coercion
            parsed = _CONFLICT_TIMES.validate_python(conflicts)
            supplied = 'conflicting_source_timestamps' in value
            if supplied:
                retained = _CONFLICT_LEXEMES.validate_python(value['conflicting_source_timestamps'])
                value = {**value, 'conflicting_source_timestamps': retained}
            lexemes = tuple(_conflict_lexeme(v, t) for v, t in zip(conflicts, parsed, strict=True))
            material = any(not _lossless_microseconds(v) for v in lexemes)
            capture = not supplied and (info.mode != 'json' or value.get('timestamp_precision') == PRECISION_CONTRACT or any(not isinstance(v, str) for v in conflicts))
            if material or (capture and conflicts):
                if material and supplied and retained and retained != lexemes:
                    raise ValueError('conflicting source timestamps conceal supplied precision')
                value = {**value, 'conflicting_source_timestamps': lexemes}
            value = {**value, 'conflicting': parsed}
        return value

    @model_validator(mode='after')
    def verified_basis(self):
        if self.timestamp_precision is not None and self.source_timestamp is None:
            raise ValueError('precision contract requires retained source timestamp')
        if self.source_timestamp is not None:
            restored = TypeAdapter(AwareDatetime).validate_python(self.source_timestamp)
            if self.recorded.value is None or restored.isoformat() != self.recorded.value.isoformat():
                raise ValueError('source timestamp contradicts retained clinical time')
        if self.conflicting_source_timestamps:
            parsed = tuple(TypeAdapter(AwareDatetime).validate_python(v).isoformat() for v in self.conflicting_source_timestamps)
            if parsed != tuple(v.isoformat() for v in self.conflicting):
                raise ValueError('conflicting timestamp evidence differs from retained times')
        if self.clock == 'verified' and self.clock_basis is None:
            raise ValueError('verified clock requires explicit evidence')
        return self

    @property
    def trustworthy(self):
        t = self.recorded
        return (_exact_source(self.source_timestamp, self.timestamp_precision)
                and len(self.conflicting_source_timestamps) == len(self.conflicting)
                and all(_exact_source(v, self.timestamp_precision) for v in self.conflicting_source_timestamps)
                and self.clock == 'verified' and t.status == 'known'
                and t.precision == 'instant' and not t.uncertainty
                and (self.alignment is None or (self.alignment.synchronization == 'synchronized'
                    and all(q is None or q.value == 0 for q in (self.alignment.offset,self.alignment.drift,self.alignment.uncertainty))))
                and all(_exact_source(a.source_timestamp, a.timestamp_precision) and a.clock == 'verified' and a.recorded.status == 'known'
                    and a.recorded.precision == 'instant' and not a.recorded.uncertainty
                    and instant(a.recorded.value) == instant(t.value) for a in self.alternative_sources)
                and all(instant(v) == instant(t.value) for v in self.conflicting))


class NumericResult(Contract):
    result_type: Literal['numeric'] = 'numeric'
    quantity: ExactQuantity
    comparator: Literal['=', '<', '<=', '>', '>='] = '='


class QualitativeResult(Contract):
    result_type: Literal['qualitative'] = 'qualitative'
    finding: RecordedConcept
    scale: SourceCode | None = None


class MissingResult(Contract):
    result_type: Literal['missing'] = 'missing'
    status: Literal['unknown', 'missing', 'not_measured', 'not_applicable']
    reason: Text


RecordedResult = Annotated[NumericResult | QualitativeResult | MissingResult,
                           Field(discriminator='result_type')]


class EvidenceQuality(Contract):
    status: Literal['acceptable', 'suspect', 'invalid', 'unknown'] = 'unknown'
    artifacts: Notes = ()
    limitations: Notes = ()
    provenance: BoundedProvenance | None = None

    @model_validator(mode='after')
    def attributed_quality(self):
        if self.status != 'unknown' and self.provenance is None:
            raise ValueError('asserted quality requires provenance')
        return self


class EvidenceBinding(Contract):
    """Scoped association; it does not automatically become an evidence edge."""
    role: Literal['device', 'calibration', 'zeroing', 'specimen', 'study', 'episode',
                  'order', 'preparation', 'dosing_weight', 'delivery', 'context']
    scope: ContextTarget
    status: Literal['resolved', 'unresolved', 'ambiguous']
    exact: Reference | None = None
    candidates: Annotated[tuple[Reference, ...], Field(max_length=16)] = ()
    provenance: BoundedProvenance
    limitation: Text | None = None

    @model_validator(mode='after')
    def shape(self):
        if self.scope.encounter_id is None:
            raise ValueError('encounter binding required')
        if self.status == 'resolved':
            if self.exact is None or self.candidates:
                raise ValueError('resolved association requires one exact target')
        elif self.exact is not None or not self.limitation:
            raise ValueError('unresolved association requires limitation')
        if self.status == 'ambiguous' and len(self.candidates) < 2:
            raise ValueError('ambiguous association needs candidates')
        if self.status == 'unresolved' and self.candidates:
            raise ValueError('unresolved association cannot assert candidates')
        if len(set(self.candidates)) != len(self.candidates):
            raise ValueError('duplicate association candidates')
        return self


class DeviceIdentity(Contract):
    identity_version: Literal['1'] = '1'
    manufacturer: SourceCode
    platform: Literal['HemoSphere', 'EV1000', 'PiCCO', 'other']
    product: SourceCode
    sensor: SourceCode | None = None
    catheter: SourceCode | None = None
    technology: Literal['FloTrac', 'AcumenIQ', 'VolumeView', 'SwanGanz', 'PiCCO', 'other']
    software: SourceCode | None = None
    serial_identity: Text | None = None
    limitations: Notes = ()


class AcquisitionApplicability(Contract):
    """Source assertion covering one exact acquisition, not a freshness heuristic."""
    acquisition: Reference
    status: Literal['applied', 'not_required', 'not_applied', 'unknown']
    available: ClinicalInstant
    provenance: BoundedProvenance


class Acquisition(Contract):
    method: Literal['invasive_arterial', 'automated_cuff', 'pac', 'rhc',
        'bolus_thermodilution', 'continuous_thermodilution', 'pulse_contour',
        'transpulmonary_thermodilution', 'direct_fick', 'indirect_fick',
        'echo', 'pocus', 'bioreactance', 'ecg_monitor', 'ecg_12_lead',
        'blood_gas', 'laboratory', 'bedside_examination', 'source_other', 'unknown']
    source_method: SourceCode | None = None
    device: DeviceIdentity | None = None
    episode: SourceCode | None = None
    parameter: SourceCode | None = None
    parameter_concept: Text | None = None
    algorithm: SourceCode | None = None
    parameter_support: Literal['source_documented', 'unsupported', 'unknown'] = 'unknown'
    support_provenance: BoundedProvenance | None = None
    site: RecordedConcept | None = None
    compartment: Literal['systemic_arterial', 'central_venous', 'right_atrial', 'right_ventricular', 'pulmonary_arterial', 'left_ventricular', 'other', 'unknown'] = 'unknown'
    laterality: Literal['left', 'right', 'midline', 'not_applicable', 'unknown'] = 'unknown'
    respiratory_phase: RecordedConcept | None = None
    position: RecordedConcept | None = None
    reference_level: RecordedConcept | None = None
    calibration: Literal['adequate', 'inadequate', 'unknown', 'not_applicable'] = 'unknown'
    zeroing: Literal['adequate', 'inadequate', 'unknown', 'not_applicable'] = 'unknown'
    calibration_application: AcquisitionApplicability | None = Field(default=None, exclude_if=lambda v: v is None)
    zeroing_application: AcquisitionApplicability | None = Field(default=None, exclude_if=lambda v: v is None)
    calibration_provenance: BoundedProvenance | None = None
    zeroing_provenance: BoundedProvenance | None = None
    interval_start: RecordedTime = Field(default_factory=missing_time)
    interval_end: RecordedTime = Field(default_factory=missing_time)
    averaging: ExactQuantity | None = None
    indexing_denominator: ExactQuantity | None = None
    indexing_basis: BoundedProvenance | None = None
    indicator: RecordedConcept | None = None
    injection: ExactQuantity | None = None
    quality: EvidenceQuality = Field(default_factory=EvidenceQuality)
    limitations: Notes = ()

    @model_validator(mode='after')
    def assertions(self):
        for name in ('calibration', 'zeroing'):
            if getattr(self, name) == 'adequate' and getattr(self, name+'_provenance') is None:
                raise ValueError('adequacy requires source evidence')
        if self.parameter_support == 'source_documented' and (self.support_provenance is None or self.parameter is None or self.parameter_concept is None):
            raise ValueError('parameter support requires source evidence')
        if self.indexing_denominator is not None and self.indexing_basis is None:
            raise ValueError('indexing denominator requires provenance')
        a, b = self.interval_start, self.interval_end
        if a.precision == b.precision == 'instant' and instant(a.value) > instant(b.value):
            raise ValueError('reversed acquisition interval')
        return self


class CirculatoryFact(PatientFact):
    contract_version: Literal['3'] = '3'
    origin: Literal['observed', 'reported']
    provenance: BoundedProvenance
    occurred: ClinicalInstant = Field(default_factory=ClinicalInstant)
    available: ClinicalInstant = Field(default_factory=ClinicalInstant)
    associations: Annotated[tuple[EvidenceBinding, ...], Field(max_length=32)] = ()
    source_identifiers: Annotated[tuple[SourceCode, ...], Field(max_length=16)] = ()
    uncertainty: Notes = ()
    disclosures: Notes = ()
    record_status: Literal['recorded', 'withdrawn', 'invalid', 'unknown'] = 'recorded'

    @model_validator(mode='after')
    def recorded_shape(self):
        if type(self) is CirculatoryFact:
            raise ValueError('concrete circulatory evidence required')
        if self.binding.target.encounter_id is None:
            raise ValueError('circulatory evidence requires encounter')
        if self.time.event or self.time.effective_start or self.time.effective_end:
            raise ValueError('use typed clinical times, not competing common event axes')
        for b in self.associations:
            if b.scope != self.binding.target or b.exact == self.reference:
                raise ValueError('association scope or self-reference invalid')
        if len(set(self.associations)) != len(self.associations):
            raise ValueError('duplicate exact association')
        from app.persistence.canonical import canonical_payload
        canonical_payload(self)
        return self

    @property
    def canonical_digest(self):
        from hashlib import sha256
        from app.persistence.canonical import canonical_payload
        return sha256(canonical_payload(self).encode()).hexdigest()


class Measurement(CirculatoryFact):
    result: RecordedResult
    acquisition: Acquisition
    production: Literal['direct_measurement', 'monitor_derived', 'source_calculated']
    calculation_method: SourceCode | None = None
    calculation_inputs: Refs = ()

    @model_validator(mode='after')
    def calculation_evidence(self):
        if self.acquisition.parameter_support == 'source_documented':
            expected_concept = 'lactate' if isinstance(self, LactateResult) else self.concept
            if self.acquisition.parameter_concept != expected_concept:
                raise ValueError('source parameter mapping contradicts measurement concept')
        if self.production == 'direct_measurement' and (self.calculation_method or self.calculation_inputs):
            raise ValueError('direct measurement cannot declare calculation')
        if len(set(self.calculation_inputs)) != len(self.calculation_inputs):
            raise ValueError('duplicate source calculation inputs')
        if not set(self.calculation_inputs) <= set(self.provenance.dependencies):
            raise ValueError('source calculation inputs require declared lineage')
        return self


class PressureObservation(Measurement):
    kind: Literal['circulatory_pressure'] = 'circulatory_pressure'
    concept: Literal['systemic_systolic', 'systemic_diastolic', 'systemic_mean',
        'pulse_pressure', 'cvp', 'rap', 'rv_systolic', 'rv_diastolic', 'pasp',
        'padp', 'mpap', 'pawp', 'lvedp', 'waveform_finding']


class CardiacPerformance(Measurement):
    kind: Literal['circulatory_cardiac'] = 'circulatory_cardiac'
    concept: Literal['co', 'ci', 'sv', 'svi', 'cpo', 'cpi', 'heart_rate', 'pulse_rate',
        'ef', 'lv_function', 'rv_function', 'pulmonary_flow', 'rv_pa_coupling',
        'svr', 'svri', 'pvr', 'pvri', 'tpg', 'dpg', 'arterial_elastance']


class VolumeMeasurement(Measurement):
    kind: Literal['circulatory_volume'] = 'circulatory_volume'
    concept: Literal['gedv', 'gedvi', 'itbv', 'itbvi', 'evlw', 'evlwi', 'pvpi',
        'gef', 'cfi', 'ventricular_volume', 'preload_estimate']


class DynamicMeasurement(Measurement):
    kind: Literal['circulatory_dynamic'] = 'circulatory_dynamic'
    concept: Literal['ppv', 'svv', 'dynamic_arterial_elastance', 'dp_dt',
        'recorded_sv_change', 'recorded_co_change']


class DevicePrediction(Measurement):
    kind: Literal['circulatory_device_prediction'] = 'circulatory_device_prediction'
    concept: Literal['hpi'] = 'hpi'
    production: Literal['monitor_derived'] = 'monitor_derived'
    disclosures: Notes = ('Source proprietary prediction; not calculated or clinically interpreted by ClinRx.',)

    @model_validator(mode='after')
    def proprietary_source(self):
        a = self.acquisition
        if a.device is None or a.device.technology != 'AcumenIQ' or a.parameter is None:
            raise ValueError('HPI requires explicit Acumen source parameter/configuration')
        if not self.disclosures:
            raise ValueError('device prediction limitation required')
        return self


class PerfusionObservation(Measurement):
    kind: Literal['circulatory_perfusion'] = 'circulatory_perfusion'
    concept: Literal['capillary_refill', 'skin_temperature', 'mottling',
        'perfusion_index', 'regional_perfusion']
    regional_site: RecordedConcept | None = None


class BloodGasContext(Contract):
    """Source-recorded respiratory context; no derived ratios or interpretation."""
    collected: ClinicalInstant
    fio2: ExactQuantity | None = None
    oxygen_device: RecordedConcept | None = None
    ventilator_mode: RecordedConcept | None = None
    peep: ExactQuantity | None = None
    provenance: BoundedProvenance
    limitations: Notes = ()


class OxygenTransport(Measurement):
    """Recorded oxygenation/gas measurements and noninvasive respiratory rate."""
    kind: Literal['circulatory_oxygen'] = 'circulatory_oxygen'
    concept: Literal['sao2', 'spo2', 'scvo2', 'svo2', 'hemoglobin', 'pao2', 'pvo2',
        'cao2', 'cvo2', 'do2', 'vo2', 'extraction_ratio',
        'ph', 'paco2', 'bicarbonate', 'base_excess', 'respiratory_rate']
    sample_type: Literal['arterial', 'central_venous', 'mixed_venous', 'peripheral_venous',
                         'noninvasive', 'unknown']
    specimen: SourceCode | None = None
    blood_gas_context: BloodGasContext | None = Field(default=None, exclude_if=lambda v: v is None)

    @model_validator(mode='after')
    def sample_identity(self):
        if self.concept == 'respiratory_rate' and (self.blood_gas_context is not None or self.acquisition.method == 'blood_gas'):
            raise ValueError('respiratory rate is a bedside observation, not a blood gas result')
        if self.blood_gas_context is not None and (self.acquisition.method != 'blood_gas' or self.sample_type == 'noninvasive'):
            raise ValueError('blood gas context requires a sampled blood gas acquisition')
        expected = {'scvo2': 'central_venous', 'svo2': 'mixed_venous',
                    'sao2': 'arterial', 'spo2': 'noninvasive', 'paco2': 'arterial',
                    'respiratory_rate': 'noninvasive'}
        if self.concept in expected and self.sample_type not in (expected[self.concept], 'unknown'):
            raise ValueError('oxygen concept contradicts sample context')
        return self


class LactateResult(Measurement):
    kind: Literal['circulatory_lactate'] = 'circulatory_lactate'
    specimen: SourceCode | None = None
    specimen_type: RecordedConcept | None = None
    sampling_site: RecordedConcept | None = None
    blood_source: Literal['arterial', 'central_venous', 'mixed_venous', 'peripheral_venous', 'other', 'unknown'] = 'unknown'
    collected: ClinicalInstant = Field(default_factory=ClinicalInstant)
    collection_assertion: BoundedProvenance | None = None
    measured: ClinicalInstant = Field(default_factory=ClinicalInstant)
    reported: ClinicalInstant = Field(default_factory=ClinicalInstant)
    analyzer: SourceCode | None = None
    report_status: Literal['final', 'preliminary', 'pending', 'cancelled', 'withdrawn', 'unknown']
    change: Literal['original', 'corrected', 'amended', 'superseded'] = 'original'

    @model_validator(mode='after')
    def correction(self):
        if self.change in ('corrected', 'amended') and self.supersedes is None:
            raise ValueError('corrected report requires exact predecessor')
        if self.supersedes is not None and self.change == 'original':
            raise ValueError('successor cannot be original report')
        return self


class EchoObservation(Measurement):
    kind: Literal['circulatory_echo'] = 'circulatory_echo'
    concept: Literal['lv_ef', 'lv_dimension', 'lv_volume', 'lvot_vti', 'sv',
        'diastolic_function', 'wall_motion', 'rv_dimension', 'rv_function', 'tapse',
        'rv_fac', 'tissue_doppler_s', 'rv_strain', 'septal_configuration', 'rv_pressure',
        'valve_finding', 'tr_measurement', 'estimated_rvsp', 'estimated_pasp', 'doppler',
        'pericardial_effusion', 'tamponade_related_finding', 'ivc_dimension',
        'ivc_variation', 'structural_finding']
    study: SourceCode
    report: SourceCode
    report_revision: Text
    view: RecordedConcept | None = None
    operator: Text | None = None
    reader: Text | None = None
    image_references: Annotated[tuple[SourceCode, ...], Field(max_length=32)] = ()


class ECGObservation(Measurement):
    kind: Literal['circulatory_ecg'] = 'circulatory_ecg'
    concept: Literal['heart_rate', 'rhythm', 'arrhythmia', 'pr', 'qrs', 'qt', 'qtc',
        'st_finding', 'conduction_finding']
    interpretation_source: Literal['monitor', 'clinician', 'source_algorithm', 'unknown']
    leads: Annotated[tuple[SourceCode, ...], Field(max_length=16)] = ()
    report: SourceCode | None = None


class VasoactiveIdentity(Contract):
    identity_version: Literal['1'] = '1'
    source: SourceCode
    canonical_id: Text | None = None
    mapping: Literal['mapped', 'unknown', 'ambiguous', 'unsupported']
    mapping_provenance: BoundedProvenance
    formulation: RecordedConcept | None = None
    limitation: Text | None = None

    @model_validator(mode='after')
    def mapped_identity(self):
        if self.mapping == 'mapped':
            if self.canonical_id is None:
                raise ValueError('mapped agent requires canonical identity')
        elif self.canonical_id is not None or not self.limitation:
            raise ValueError('unresolved identity requires limitation, no asserted mapping')
        return self


class DeliveryDetails(Contract):
    route: RecordedConcept | None = None
    concentration: ExactQuantity | None = None
    rate: ExactQuantity | None = None
    amount: ExactQuantity | None = None
    dosing_weight_basis: Literal['actual', 'ideal', 'adjusted', 'source_other', 'unknown'] = 'unknown'
    dosing_weight: Reference | None = None
    pump: SourceCode | None = None
    channel: SourceCode | None = None
    infusion: SourceCode | None = None
    attestation: BoundedProvenance | None = None


class OrderEvent(Contract):
    event_type: Literal['order'] = 'order'
    prescribed: DeliveryDetails
    status: RecordedConcept


class PreparationEvent(Contract):
    event_type: Literal['preparation'] = 'preparation'
    prepared: DeliveryDetails


class InfusionEvent(Contract):
    event_type: Literal['initiation', 'rate_change', 'restart', 'bolus']
    delivery: DeliveryDetails


class InterruptionEvent(Contract):
    event_type: Literal['pause', 'permanent_stop', 'non_delivery']
    reason: RecordedConcept
    attestation: BoundedProvenance | None = None


VasoactiveAction = Annotated[OrderEvent | PreparationEvent | InfusionEvent | InterruptionEvent,
                            Field(discriminator='event_type')]


class VasoactiveEvent(CirculatoryFact):
    kind: Literal['circulatory_vasoactive'] = 'circulatory_vasoactive'
    drug: VasoactiveIdentity
    action: VasoactiveAction
    source_status: RecordedConcept


class MonitoringEvent(CirculatoryFact):
    kind: Literal['circulatory_monitoring'] = 'circulatory_monitoring'
    device: DeviceIdentity
    event_type: Literal['configuration', 'calibration', 'zeroing', 'quality_change']
    acquisition: Acquisition
    finding: RecordedConcept


class DynamicAssessment(CirculatoryFact):
    kind: Literal['circulatory_assessment'] = 'circulatory_assessment'
    test: Literal['plr', 'end_expiratory_occlusion', 'mini_fluid_challenge', 'fluid_challenge']
    protocol: SourceCode
    baseline: Refs
    intervention: Refs
    subsequent: Refs
    ventilation_mode: RecordedConcept | None = None
    tidal_volume: ExactQuantity | None = None
    tidal_volume_basis: Text | None = None
    rhythm: RecordedConcept | None = None
    spontaneous_effort: Literal['present', 'absent', 'unknown'] = 'unknown'
    position: RecordedConcept | None = None
    quality: EvidenceQuality = Field(default_factory=EvidenceQuality)
    reported_interpretation: RecordedConcept | None = None
    interpretation_provenance: BoundedProvenance | None = None

    @model_validator(mode='after')
    def attributed_interpretation(self):
        if self.reported_interpretation and self.interpretation_provenance is None:
            raise ValueError('source interpretation requires provenance')
        return self


class RecordedCirculatoryInterval(Contract):
    """Source-asserted boundaries, not a derived duration or verified ordering."""
    start: ClinicalInstant
    end: ClinicalInstant
    provenance: BoundedProvenance
    limitations: Notes = ()


class CirculatoryEvent(CirculatoryFact):
    kind: Literal['circulatory_event'] = 'circulatory_event'
    event_type: Literal['fluid_bolus', 'fluid_challenge', 'transfusion', 'bleeding',
        'arrhythmia', 'arrest', 'cardioversion', 'pacing', 'reperfusion', 'surgery',
        'transplantation', 'ventilation_change', 'crrt_start', 'crrt_interruption',
        'position_change', 'other']
    description: RecordedConcept
    external_evidence: Annotated[tuple[SourceCode, ...], Field(max_length=32)] = ()
    recorded_amount: ExactQuantity | None = None
    recorded_interval: RecordedCirculatoryInterval | None = Field(default=None, exclude_if=lambda v: v is None)


class SignalManifest(CirculatoryFact):
    kind: Literal['circulatory_signal'] = 'circulatory_signal'
    signal: Literal['ecg', 'arterial_pressure', 'cvp', 'pap', 'beat_to_beat', 'monitor_trend']
    device: DeviceIdentity
    channel: SourceCode
    start: ClinicalInstant
    end: ClinicalInstant
    sample_rate: ExactQuantity | None = None
    sample_count: Annotated[int, Field(strict=True, ge=0)] | None = None
    units: RecordedConcept
    encoding: SourceCode
    content: SourceCode | None = None
    content_sha256: Annotated[str, Field(pattern='^[0-9a-f]{64}$')] | None = None
    availability: Literal['available', 'unavailable', 'unknown']
    gaps: Annotated[tuple[RecordedTime, ...], Field(max_length=64)] = ()
    quality: EvidenceQuality = Field(default_factory=EvidenceQuality)

    @model_validator(mode='after')
    def integrity_reference(self):
        if self.availability == 'available' and (self.content is None or self.content_sha256 is None):
            raise ValueError('available segment requires content and integrity reference')
        if self.sample_rate is not None and self.sample_rate.value <= 0:
            raise ValueError('sample frequency must be positive')
        if self.start.trustworthy and self.end.trustworthy:
            if instant(self.start.recorded.value) > instant(self.end.recorded.value):
                raise ValueError('signal interval reversed')
        return self


CirculatoryRecord = Annotated[PressureObservation | CardiacPerformance | VolumeMeasurement |
    DynamicMeasurement | DevicePrediction | PerfusionObservation | OxygenTransport |
    LactateResult | EchoObservation | ECGObservation | VasoactiveEvent | MonitoringEvent |
    DynamicAssessment | CirculatoryEvent | SignalManifest, Field(discriminator='kind')]

# Explicit persistence admission; not a clinical-policy registry.
M7_FACTS = {m.model_fields['kind'].default: m for m in (
    PressureObservation, CardiacPerformance, VolumeMeasurement, DynamicMeasurement,
    DevicePrediction, PerfusionObservation, OxygenTransport, LactateResult,
    EchoObservation, ECGObservation, VasoactiveEvent, MonitoringEvent,
    DynamicAssessment, CirculatoryEvent, SignalManifest)}
