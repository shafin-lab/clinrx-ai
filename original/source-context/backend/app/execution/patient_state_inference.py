"""Pure explicit-subset descriptive inference; consistency is not authentication."""
from datetime import timezone
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from app.execution.patient_state import LaboratoryState, MedicationState, PatientStateScope
from app.execution.patient_state_assembly import PatientStateAssemblyResult
from app.models.clinical.common import (
    ClinicalTime, DomainModel, LineageEdge, Provenance, Quantity, Reference, Source, Text,
)
from app.models.clinical.facts import ClinicalInference
from app.persistence.mapping import canonical_payload

METHOD = Reference(kind='inference_method', id='RecordedPatientStateTemporalRelation', version='1')
APPLICABILITY = ('Descriptive comparison of two explicitly selected recorded serum-creatinine observations '
                 'and one selected medication event within the supplied patient/encounter snapshot only.')
MANDATORY_UNCERTAINTY = (
    'Recorded and explicitly selected evidence only; this is not a patient-wide summary.',
    'Source completeness is unknown; additional evidence may exist in unsupported or unmapped domains.',
    'Mapping omissions are not evaluated as evidence of clinical absence.',
    'Availability by review end is not established.',
    'Temporal ordering does not establish clinical significance or cause.',
    'Source authenticity and specimen independence are not independently established.',
)
VALIDATION_LIMITATION = ('Not clinically validated; no diagnosis, causal attribution, medication-effect '
                         'assessment or treatment recommendation.')
Reason = Literal['invalid_request', 'invalid_assembly', 'scope_mismatch',
                 'selected_reference_missing', 'selected_domain_mismatch', 'selected_content_mismatch',
                 'duplicate_selected_measurement', 'unsupported_unit', 'invalid_event_timing',
                 'invalid_laboratory_order', 'medication_not_strictly_between', 'invalid_execution_time']


class PatientStateTemporalInferenceError(ValueError):
    """Bounded public error; never includes supplied evidence in its message."""
    def __init__(self, code: Reason):
        self.code = code
        super().__init__(code)


class PatientStateSelectionPin(DomainModel):
    reference: Reference
    expected_digest: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]


class PatientStateTemporalRelationRequest(DomainModel):
    scope: PatientStateScope
    earlier_laboratory: PatientStateSelectionPin
    later_laboratory: PatientStateSelectionPin
    medication: PatientStateSelectionPin
    inference_id: Text
    revision: Text = '1'
    executed_at: AwareDatetime
    supersedes: Reference | None = None
    correction_reason: Text | None = None

    @model_validator(mode='after')
    def correction_pair(self):
        if (self.supersedes is None) != (self.correction_reason is None):
            raise ValueError('correction requires a pair')
        if self.supersedes is not None and (
                self.supersedes.kind != 'inference' or self.supersedes.id != self.inference_id
                or self.supersedes.version == self.revision):
            raise ValueError('correction requires a different revision of the same inference')
        canonical_payload(self)
        return self


def _instant(value):
    return value.astimezone(timezone.utc)


def _selected(snapshot, pin, domain):
    matches = tuple(item for item in getattr(snapshot, domain) if item.reference == pin.reference)
    if len(matches) != 1:
        code = ('selected_domain_mismatch' if any(item.reference == pin.reference for item in snapshot.ordered_items)
                else 'selected_reference_missing')
        raise PatientStateTemporalInferenceError(code)
    item = matches[0]
    if item.canonical_digest != pin.expected_digest:
        raise PatientStateTemporalInferenceError('selected_content_mismatch')
    if item.time.event is None or item.time.precision != 'instant' or item.time.uncertainty is not None:
        raise PatientStateTemporalInferenceError('invalid_event_timing')
    return item


def _laboratory(item):
    payload, source = item.payload, item.provenance.source
    if type(payload) is not LaboratoryState or item.reference.kind != 'observation':
        raise PatientStateTemporalInferenceError('selected_domain_mismatch')
    if (payload.concept_id != 'synthetic-serum-creatinine'
            or source.namespace != 'clinrx.synthetic.serum-creatinine' or source.version != '1'
            or source.channel not in ('measurement', 'external_record')
            or payload.value.status != 'known' or not isinstance(payload.value.value, Quantity)):
        raise PatientStateTemporalInferenceError('selected_content_mismatch')
    quantity = payload.value.value
    unit = quantity.unit
    if (unit.raw != 'mg/dL' or unit.code != 'mg/dL' or unit.system != 'UCUM'
            or unit.status not in ('assessed', 'normalized')):
        raise PatientStateTemporalInferenceError('unsupported_unit')
    return quantity.value


def _build(assembly, request):
    snapshot = assembly.snapshot
    if canonical_payload(request.scope) != canonical_payload(snapshot.scope):
        raise PatientStateTemporalInferenceError('scope_mismatch')
    a = _selected(snapshot, request.earlier_laboratory, 'laboratory')
    b = _selected(snapshot, request.later_laboratory, 'laboratory')
    m = _selected(snapshot, request.medication, 'medication')
    av, bv = _laboratory(a), _laboratory(b)
    if (a.reference.id == b.reference.id or
            (a.provenance.source.namespace, a.provenance.source.identifier) ==
            (b.provenance.source.namespace, b.provenance.source.identifier)):
        raise PatientStateTemporalInferenceError('duplicate_selected_measurement')
    if type(m.payload) is not MedicationState or m.reference.kind not in ('medication_order', 'medication_administration'):
        raise PatientStateTemporalInferenceError('selected_domain_mismatch')
    if m.reference.kind == 'medication_administration' and (
            m.payload.status != 'administered' or m.payload.dose is None
            or m.payload.dose.basis != 'total_administered'):
        raise PatientStateTemporalInferenceError('selected_content_mismatch')
    ta, tb, tm = a.time.event, b.time.event, m.time.event
    if not _instant(ta) < _instant(tb):
        raise PatientStateTemporalInferenceError('invalid_laboratory_order')
    if not _instant(ta) < _instant(tm) < _instant(tb):
        raise PatientStateTemporalInferenceError('medication_not_strictly_between')
    for item in (a, b, m):
        relevant = (item.time.event, item.time.recorded, item.time.retrieved, item.time.processed,
                    item.provenance.recorded_at, item.binding.verification.assessed_at)
        if any(_instant(request.executed_at) < _instant(t) for t in relevant if t is not None):
            raise PatientStateTemporalInferenceError('invalid_execution_time')
    if av == bv:
        statement = (f'Recorded serum creatinine was unchanged between the selected laboratory observations '
                     f'at {ta.isoformat()} and {tb.isoformat()} ({av} mg/dL then {bv} mg/dL).')
    else:
        direction = 'increased' if bv > av else 'decreased'
        statement = (f'Recorded serum creatinine {direction} from {av} mg/dL to {bv} mg/dL between the '
                     f'selected laboratory observations at {ta.isoformat()} and {tb.isoformat()}.')
    if m.reference.kind == 'medication_order':
        statement += f' The selected medication order has a recorded event time of {tm.isoformat()}, strictly between those observations.'
    else:
        statement += f' The selected medication administration has a recorded administration time of {tm.isoformat()}, strictly between those observations.'
    statement += ' Temporal ordering does not establish clinical significance or cause. Synthetic evaluation only.'
    uncertainty = list(MANDATORY_UNCERTAINTY)
    for label, item in zip(('A', 'B', 'M'), (a, b, m), strict=True):
        uncertainty.extend(item.disclosures)
        uncertainty.extend(item.provenance.limitations)
        uncertainty.extend((f'Selected {label} verification: {item.verification}.',
                            f'Selected {label} conflict: {item.conflict}.',
                            f'Selected {label} provenance completeness: {item.provenance.lineage}.',
                            f'Selected {label} binding verification: {item.binding.verification.status}.'))
    inputs = (a.reference, b.reference, m.reference)
    result = ClinicalInference(
        id=request.inference_id, revision=request.revision, binding=a.binding, origin='inferred',
        statement=statement, inputs=inputs, method=METHOD, applicability=APPLICABILITY,
        uncertainty=tuple(dict.fromkeys(uncertainty)), validation_limitations=VALIDATION_LIMITATION,
        supersedes=request.supersedes, correction_reason=request.correction_reason,
        provenance=Provenance(source=Source(namespace='clinrx.synthetic', identifier=METHOD.id, version='1', channel='system'),
            actor='RecordedPatientStateTemporalRelation/v1', recorded_at=request.executed_at,
            upstream=tuple(LineageEdge(target=ref, relationship='derived_from') for ref in inputs),
            lineage='complete', limitations=('Direct selected dependencies only; source authenticity and complete ancestry are not established.',)),
        time=ClinicalTime(event=request.executed_at, recorded=request.executed_at, processed=request.executed_at, precision='instant'),
        verification='unverified', conflict='unknown', temporal_status='unknown',
    )
    if result.inputs != inputs or result.provenance.dependencies != inputs:
        raise PatientStateTemporalInferenceError('selected_content_mismatch')
    canonical_payload(result)
    return result


def build_patient_state_temporal_inference(*, assembly: PatientStateAssemblyResult,
                                          request: PatientStateTemporalRelationRequest) -> ClinicalInference:
    """Validate supplied membership/digests, then describe exactly A/B/M.

    No source authentication, database access, clock sampling or release decision.
    Exception messages/chained display are bounded; Python introspection of exception
    contexts or traceback locals is not a privacy boundary.
    """
    try:
        if type(request) is not PatientStateTemporalRelationRequest:
            raise ValueError
        request = PatientStateTemporalRelationRequest.model_validate(request)
    except Exception:
        raise PatientStateTemporalInferenceError('invalid_request') from None
    try:
        if type(assembly) is not PatientStateAssemblyResult:
            raise ValueError
        assembly = PatientStateAssemblyResult.model_validate(assembly)
    except Exception:
        raise PatientStateTemporalInferenceError('invalid_assembly') from None
    try:
        return _build(assembly, request)
    except PatientStateTemporalInferenceError:
        raise
    except Exception:
        raise PatientStateTemporalInferenceError('selected_content_mismatch') from None
