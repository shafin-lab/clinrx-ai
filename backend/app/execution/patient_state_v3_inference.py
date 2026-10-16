"""RecordedPressureLactateVasopressorTiming/v1: pure approved synthetic eligibility."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from app.models.clinical.common import Reference, LineageEdge, Provenance, Source, Text
from app.models.clinical.facts import ClinicalInference
from app.models.clinical import hemodynamics as h
from app.models.clinical.recorded_v2 import Contract, Digest, instant, ref_key
from app.persistence.canonical import canonical_payload
from .patient_state_v3_support import consumed_binding_roles, consumed_provenance_references
from .patient_state_v3 import PatientStateScopeV3
from .patient_state_v3_assembly import PatientStateAssemblyResultV3

POLICY_VERSION = 'SyntheticPLVEligibility/1'

METHOD = Reference(kind='inference_method',id='RecordedPressureLactateVasopressorTiming',version='1')
LIMITATIONS = (
    'Synthetic descriptive timing of exact selected recorded evidence only.',
    'No shock diagnosis, causality, response, continuous exposure, appropriateness or treatment recommendation.',
    'Source authenticity and completeness are not established.',
)


class CirculatoryInferenceError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code='unsuitable_evidence'):
    if not condition:
        raise CirculatoryInferenceError(code)


class EvidencePin(Contract):
    reference: Reference
    expected_digest: Digest


class CirculatoryTimingRequest(Contract):
    eligibility_policy: Annotated[Literal['SyntheticPLVEligibility/1'] | None, Field(exclude_if=lambda v: v is None)] = None
    scope: PatientStateScopeV3
    pressure: EvidencePin
    lactate: EvidencePin
    vasopressor: EvidencePin
    supporting: Annotated[tuple[EvidencePin, ...], Field(max_length=32)] = ()
    expected_assembly_digest: Digest
    inference_id: Text
    revision: Text = '1'
    executed_at: AwareDatetime

    @model_validator(mode='after')
    def unique(self):
        refs = self.inputs
        if len({(r.kind,r.id) for r in refs}) != len(refs):
            raise ValueError('duplicate stable inference dependency')
        if self.supporting != tuple(sorted(self.supporting,key=lambda p:ref_key(p.reference))):
            raise ValueError('supporting evidence must be in exact reference order')
        return self

    @property
    def pins(self):
        return (self.pressure,self.lactate,self.vasopressor,*self.supporting)

    @property
    def inputs(self):
        return tuple(p.reference for p in self.pins)


def required_support(fact):
    """Require pins for each consumed binding and its supporting provenance."""
    refs = set(consumed_provenance_references(fact))
    for binding in fact.associations:
        if binding.role in consumed_binding_roles(fact):
            require(binding.status == 'resolved', 'unresolved_required_binding')
            refs.add(binding.exact)
    return refs


def _unit(result, raw, code):
    require(isinstance(result,h.NumericResult) and result.comparator == '=')
    u=result.quantity.unit
    require(u.raw == raw and (u.status == 'unresolved' or (u.system == 'UCUM' and u.code == code)), 'unsupported_unit')


def _exact(t):
    require(t.trustworthy,'untrustworthy_clinical_time')
    return t.recorded.value


def _build_circulatory_timing_inference(*, assembly, request):
    assembly=PatientStateAssemblyResultV3.model_validate(assembly)
    request=CirculatoryTimingRequest.model_validate(request)
    require(request.eligibility_policy == POLICY_VERSION, 'unapproved_eligibility_policy')
    require(canonical_payload(assembly.request.scope)==canonical_payload(assembly.snapshot.scope),'invalid_assembly')
    require(canonical_payload(request.scope)==canonical_payload(assembly.request.scope),'scope_mismatch')
    require(assembly.canonical_digest==request.expected_assembly_digest,'assembly_digest_mismatch')
    items={i.reference:i for i in assembly.snapshot.items}
    consumed=[]
    for pin in request.pins:
        require(pin.reference in items,'missing_selected_evidence')
        item=items[pin.reference]
        require(item.expected_digest==pin.expected_digest==item.fact.canonical_digest,'evidence_digest_mismatch')
        f=item.fact
        require(f.binding.target==request.scope.target and f.binding.verification.status=='verified','unverified_binding')
        require(f.record_status=='recorded' and f.conflict not in ('unresolved',), 'invalid_selected_status')
        require(instant(f.provenance.recorded_at)<=instant(request.executed_at),'future_recording')
        axes=(f.available, f.occurred)
        if isinstance(f,h.LactateResult):axes=(*axes,f.collected,f.measured,f.reported)
        for axis in axes:
            t=axis.recorded
            if t.status=='known':
                upper=t.upper or t.value
                require(upper is not None and instant(upper)<=instant(request.executed_at),'future_availability')
        consumed.append(f)
    p,l,v=consumed[:3]
    require(type(p) is h.PressureObservation and type(l) is h.LactateResult and type(v) is h.VasoactiveEvent,'wrong_evidence_role')
    require(p.concept in ('systemic_systolic','systemic_diastolic','systemic_mean'))
    require(p.acquisition.method in ('invasive_arterial','automated_cuff'))
    require(p.acquisition.compartment in ('systemic_arterial','unknown'),'pressure_site_mismatch')
    if p.acquisition.device is not None:
        require(p.acquisition.parameter_support=='source_documented','unsupported_device_parameter')
    _unit(p.result,'mmHg','mm[Hg]')
    quality=p.acquisition.quality
    require(quality.status=='acceptable' and not quality.artifacts,'pressure_quality')
    if p.acquisition.method=='invasive_arterial':
        require(p.acquisition.calibration=='adequate' and p.acquisition.zeroing=='adequate','pressure_calibration')
    require(l.acquisition.quality.status=='acceptable' and not l.acquisition.quality.artifacts,'invalid_lactate_quality')
    # Applicability covers this exact acquisition, including retrospective source
    # attestations. Availability is evaluated separately from acquisition time.
    for name in (('calibration','zeroing') if p.acquisition.method=='invasive_arterial' else ('calibration',)):
        application=getattr(p.acquisition,name+'_application')
        require(application is not None and application.acquisition==p.reference,'unknown_acquisition_applicability')
        require(application.status=='applied' or
            (p.acquisition.method=='automated_cuff' and application.status=='not_required'), 'unknown_acquisition_applicability')
        if application.status=='applied':
            require(getattr(p.acquisition,name)=='adequate','pressure_calibration')
        require(h._exact_source(application.available.source_timestamp,application.available.timestamp_precision),'unavailable_acquisition_attestation')
        available=application.available.recorded
        require(available.status=='known' and available.precision=='instant' and
            available.value is not None and instant(available.value)<=instant(request.executed_at), 'unavailable_acquisition_attestation')
        require(instant(application.provenance.recorded_at)<=instant(request.executed_at),'future_acquisition_attestation')
    expected_compartment={'arterial':'systemic_arterial','central_venous':'central_venous','mixed_venous':'pulmonary_arterial'}.get(l.blood_source)
    if expected_compartment is not None and l.acquisition.compartment!='unknown':
        require(l.acquisition.compartment==expected_compartment,'lactate_site_mismatch')
    require(l.report_status=='final' and l.change!='superseded','lactate_status')
    require(l.specimen is not None or l.collection_assertion is not None,'missing_specimen_assertion')
    _unit(l.result,'mmol/L','mmol/L')
    require(l.result.quantity.value>=0,'invalid_lactate_quantity')
    require(isinstance(v.action,h.InfusionEvent) and v.action.event_type=='initiation','not_actual_initiation')
    require(v.action.delivery.attestation is not None,'missing_delivery_attestation')
    require(v.drug.mapping=='mapped' and v.drug.canonical_id is not None,'unresolved_drug_identity')
    # This initial method supports the explicitly named vasopressors, not all inotropes.
    require(v.drug.canonical_id in ('norepinephrine','epinephrine','vasopressin','phenylephrine','dopamine'), 'unsupported_vasopressor_identity')
    times=(_exact(p.occurred),_exact(l.collected),_exact(v.occurred))
    require(all(instant(t)<=instant(request.executed_at) for t in times),'future_event')
    required=set()
    graph={}
    for f in consumed:
        graph[f.reference]=required_support(f)
        required.update(graph[f.reference])
    visited=set()
    def acyclic(ref,path):
        require(ref not in path,'cyclic_supporting_evidence')
        if ref in visited: return
        for parent in graph.get(ref,()):
            if parent in graph: acyclic(parent,path | {ref})
        visited.add(ref)
    for f in consumed: acyclic(f.reference,set())
    require(required - set(request.inputs[:3]) == set(request.inputs[3:]), 'supporting_dependency_mismatch')
    # Bindings cannot claim an unrelated support type or an inconsistent source assertion.
    by_ref={f.reference:f for f in consumed}
    for owner in consumed:
        for binding in owner.associations:
            if binding.role in consumed_binding_roles(owner):
                require(binding.exact in by_ref,'missing_supporting_dependency')
                support=by_ref[binding.exact]
                if binding.role in ('device','calibration','zeroing'):
                    require(isinstance(support,h.MonitoringEvent),'wrong_supporting_type')
                    if binding.role in ('calibration','zeroing'):
                        require(support.event_type==binding.role,'wrong_supporting_type')
                        require(getattr(support.acquisition,binding.role)=='adequate','invalid_supporting_calibration')
                    if getattr(owner,'acquisition',None) and owner.acquisition.device is not None:
                        require(support.device==owner.acquisition.device,'device_configuration_mismatch')
                elif binding.role=='delivery':
                    require(isinstance(support,h.VasoactiveEvent) and isinstance(support.action,h.InfusionEvent)
                        and support.action.event_type=='initiation' and support.action.delivery.attestation is not None,'wrong_supporting_type')
                    require(support.drug==owner.drug,'delivery_identity_mismatch')
                    require(support.action.delivery.pump==owner.action.delivery.pump
                        and support.action.delivery.channel==owner.action.delivery.channel,'delivery_channel_mismatch')
                else:
                    # An external specimen not admitted by v3 cannot be hidden as context.
                    require(False,'unsupported_specimen_dependency')
    def relation(t):
        return 'before' if instant(t)<instant(times[2]) else 'after' if instant(t)>instant(times[2]) else 'at'
    statement=(f'The selected pressure observation was recorded as acquired at {times[0].isoformat()}. '
        f'The selected lactate sample was recorded as collected at {times[1].isoformat()}. '
        f'The selected vasopressor initiation was documented at {times[2].isoformat()}. '
        f'Pressure acquisition occurred {relation(times[0])} the initiation event. '
        f'Lactate collection occurred {relation(times[1])} the initiation event.')
    return ClinicalInference(id=request.inference_id,revision=request.revision,
        binding=p.binding, origin='inferred', temporal_status='historical',
        time=dict(precision='instant',event=request.executed_at,recorded=request.executed_at,processed=request.executed_at),
        provenance=Provenance(source=Source(namespace='clinrx.synthetic',identifier=METHOD.id,version='1',channel='system'),
            actor=METHOD.id,recorded_at=request.executed_at,lineage='incomplete',limitations=LIMITATIONS,
            upstream=tuple(LineageEdge(target=r,relationship='derived_from') for r in request.inputs)),
        statement=statement,inputs=request.inputs,method=METHOD,
        applicability='Exact selected P/L/V events and explicitly consumed supporting revisions only.',
        uncertainty=tuple(f'{pin.reference.kind}/{pin.reference.id}/{pin.reference.version}:sha256:{pin.expected_digest}' for pin in request.pins),
        validation_limitations='Synthetic structural validation only; not approved for patient care.')


def build_circulatory_timing_inference(*, assembly, request):
    """Pure bounded input boundary; operational limits are never suitability issues."""
    from pydantic import ValidationError
    from app.persistence.errors import PersistenceInputError, UnsupportedOperation
    try:
        return _build_circulatory_timing_inference(assembly=assembly, request=request)
    except (ValidationError, ValueError, TypeError, PersistenceInputError, UnsupportedOperation):
        raise CirculatoryInferenceError('invalid_contract') from None
