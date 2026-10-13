"""Pure four-role recorded timing; consistency checks do not authenticate sources."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from app.execution.patient_state_v2 import PatientStateScopeV2
from app.execution.patient_state_v2_assembly import PatientStateAssemblyResultV2
from app.models.clinical.recorded_v2 import Contract, Digest, instant
from app.models.clinical.microbiology import Specimen, IsolateIdentification, SusceptibilityResult
from app.models.clinical.antimicrobials import CompletedAntimicrobialAdministration
from app.models.clinical.common import ClinicalTime, LineageEdge, Provenance, Reference, Source, Text
from app.models.clinical.facts import ClinicalInference
from app.persistence.canonical import canonical_payload

METHOD = Reference(kind='inference_method', id='RecordedAntimicrobialSpecimenSusceptibilityTiming', version='1')
APPLICABILITY = ('Descriptive timing of exactly the selected specimen, isolate identification, '
    'susceptibility revision and completed antimicrobial administration in the supplied synthetic encounter.')
MANDATORY_UNCERTAINTY = (
    'Does not establish treatment appropriateness.',
    'Does not establish infection versus colonization.',
    'Does not establish source authenticity or complete source coverage.',
    'Does not establish clinician awareness.',
    'Does not establish causality.',
    'Does not establish complete antimicrobial exposure.',
    'Does not establish that the selected susceptibility was clinically actionable.',
    'Does not establish breakpoint validity beyond recorded source metadata.',
)
VALIDATION_LIMITATION = 'Synthetic descriptive comparison only; not clinically validated and not a treatment recommendation.'
Role = Literal['S', 'I', 'U', 'D']
Relation = Literal['before', 'at', 'after']
Reason = Literal['invalid_request', 'invalid_assembly', 'assembly_digest_mismatch', 'scope_mismatch',
    'selected_reference_missing', 'selected_role_type', 'selected_digest_mismatch',
    'unsupported_binding', 'unsupported_antimicrobial_mapping', 'antimicrobial_identity_mismatch',
    'missing_required_time', 'insufficient_temporal_precision', 'ambiguous_temporal_relation',
    'unsupported_report_state', 'unresolved_conflict', 'invalid_execution_time', 'evidence_limits_exceeded']


class MicroAntimicrobialInferenceError(ValueError):
    """Bounded error code/category, without evidence in the displayed exception."""
    def __init__(self, code: Reason):
        self.code = code
        self.category = ('invalid_input' if code == 'invalid_request' else
            'integrity' if code in ('invalid_assembly', 'assembly_digest_mismatch',
                'scope_mismatch', 'selected_digest_mismatch') else 'unsuitable')
        super().__init__(code)


class MicroAntimicrobialPin(Contract):
    role: Role
    reference: Reference
    expected_digest: Digest


class MicroAntimicrobialTimingRequest(Contract):
    scope: PatientStateScopeV2
    profile_id: Literal['SyntheticMicrobiologyAntimicrobialState'] = 'SyntheticMicrobiologyAntimicrobialState'
    profile_version: Literal['2'] = '2'
    expected_assembly_digest: Digest
    specimen_ref: MicroAntimicrobialPin
    isolate_ref: MicroAntimicrobialPin
    susceptibility_ref: MicroAntimicrobialPin
    administration_ref: MicroAntimicrobialPin
    inference_id: Annotated[Text, Field(max_length=256)]
    revision: Annotated[Text, Field(max_length=128)] = '1'
    executed_at: AwareDatetime
    supersedes: Reference | None = None
    correction_reason: Annotated[Text, Field(max_length=4096)] | None = None

    @model_validator(mode='after')
    def roles_and_revision(self):
        pins = (self.specimen_ref, self.isolate_ref, self.susceptibility_ref, self.administration_ref)
        if tuple(p.role for p in pins) != ('S', 'I', 'U', 'D'):
            raise ValueError('named selection roles must be S/I/U/D')
        if len({p.reference for p in pins}) != 4:
            raise ValueError('four distinct exact role references required')
        if (self.supersedes is None) != (self.correction_reason is None):
            raise ValueError('correction requires predecessor and reason')
        if self.supersedes and (self.supersedes.kind != 'inference' or self.supersedes.id != self.inference_id
                or self.supersedes.version == self.revision):
            raise ValueError('correction requires another revision of this inference')
        return self


def _fail(code):
    raise MicroAntimicrobialInferenceError(code)


def _assembly(assembly, request):
    if type(assembly) is not PatientStateAssemblyResultV2:
        _fail('invalid_assembly')
    try:
        assembly = PatientStateAssemblyResultV2.model_validate(assembly)
    except Exception:
        raise MicroAntimicrobialInferenceError('invalid_assembly') from None
    snapshot = assembly.snapshot
    if (assembly.request.profile_id, assembly.request.profile_version) != (request.profile_id, request.profile_version):
        _fail('scope_mismatch')
    if canonical_payload(snapshot.scope) != canonical_payload(request.scope):
        _fail('scope_mismatch')
    # Pin the full normalized collection before any subset selection. This is
    # integrity checking of supplied content, not a claim of authenticated origin.
    if assembly.canonical_digest != request.expected_assembly_digest:
        _fail('assembly_digest_mismatch')
    limits = assembly.request.limits
    if (assembly.candidate_rows > limits.history.max_rows or len(snapshot.items) > limits.max_items
            or len(assembly.bindings) > limits.max_bindings
            or len(assembly.issues) + len(snapshot.issues) > limits.max_issues
            or len(canonical_payload(assembly).encode('utf-8')) > limits.max_result_bytes):
        _fail('invalid_assembly')
    if ({c.domain for c in snapshot.coverage} != {'microbiology', 'antimicrobial'}
            or any(c.retrieval != 'completed' for c in snapshot.coverage)):
        _fail('invalid_assembly')
    if sum(c.candidate_count for c in snapshot.coverage) > assembly.terminal_count:
        _fail('invalid_assembly')
    items = {i.reference: i for i in snapshot.items}
    declared = {(i.reference, b.role): b for i in snapshot.items for b in i.fact.domain_bindings}
    outcomes = {(b.owner, b.role): b for b in assembly.bindings}
    if len(outcomes) != len(assembly.bindings) or set(outcomes) != set(declared):
        _fail('invalid_assembly')
    for key, binding in declared.items():
        outcome = outcomes[key]
        if outcome.declared != binding.exact or outcome.candidates != binding.candidates:
            _fail('invalid_assembly')
        if binding.status != 'resolved':
            if outcome.status != binding.status or outcome.disposition != 'declared_' + binding.status:
                _fail('invalid_assembly')
        elif binding.exact in items:
            if outcome.status != 'resolved' or outcome.disposition != 'retained_exact':
                _fail('invalid_assembly')
        elif outcome.disposition == 'unavailable_in_prefix':
            if outcome.status != 'unresolved':
                _fail('invalid_assembly')
        elif outcome.disposition not in ('historical_exact_not_retained', 'outside_profile', 'withdrawn_target_not_retained') or outcome.status != 'resolved':
            _fail('invalid_assembly')
    return assembly


def _select(assembly, pin, model):
    expected_kind = model.model_fields['kind'].default
    if pin.reference.kind != expected_kind:
        _fail('selected_role_type')
    item = next((i for i in assembly.snapshot.items if i.reference == pin.reference), None)
    if item is None:
        _fail('selected_reference_missing')
    if type(item.fact) is not model:
        _fail('selected_role_type')
    if item.fact.canonical_digest != pin.expected_digest or item.expected_digest != pin.expected_digest:
        _fail('selected_digest_mismatch')
    return item


def _bound(child, role, parent):
    binding = next((b for b in child.domain_bindings if b.role == role), None)
    if binding is None or binding.status != 'resolved' or binding.exact != parent.reference:
        _fail('unsupported_binding')


def _range(time):
    if time.status != 'known':
        _fail('missing_required_time')
    if time.precision == 'instant' and time.uncertainty is None:
        return instant(time.value), instant(time.value)
    if time.precision == 'bounded':
        return instant(time.lower), instant(time.upper)
    # Free-text uncertainty around a representative approximate/day value is
    # not a machine-readable bound. Never invent an uncertainty interval.
    _fail('insufficient_temporal_precision')


def _relation(left, right) -> Relation:
    if left[1] < right[0]:
        return 'before'
    if left[0] > right[1]:
        return 'after'
    if left[0] == left[1] == right[0] == right[1]:
        return 'at'
    _fail('ambiguous_temporal_relation')


def _time_text(time):
    if time.precision == 'instant':
        return 'at ' + time.value.isoformat()
    return 'within [' + time.lower.isoformat() + ', ' + time.upper.isoformat() + ']'


def _build(assembly, request):
    assembly = _assembly(assembly, request)
    s = _select(assembly, request.specimen_ref, Specimen)
    i = _select(assembly, request.isolate_ref, IsolateIdentification)
    u = _select(assembly, request.susceptibility_ref, SusceptibilityResult)
    d = _select(assembly, request.administration_ref, CompletedAntimicrobialAdministration)
    selected = (s, i, u, d)
    sf, inf, uf, df = (item.fact for item in selected)
    _bound(inf, 'specimen', sf)
    _bound(uf, 'isolate', inf)
    if (inf.report.status != 'final' or inf.identification_state != 'final'
            or uf.report.status != 'final' or uf.result_status != 'reported'
            or inf.report.change == 'superseded' or uf.report.change == 'superseded'):
        _fail('unsupported_report_state')
    if any(item.fact.conflict == 'unresolved' for item in selected):
        _fail('unresolved_conflict')
    tested, administered = uf.antimicrobial, df.antimicrobial
    if tested.mapping_status != 'mapped' or administered.mapping_status != 'mapped':
        _fail('unsupported_antimicrobial_mapping')
    if (tested.identity_version, tested.canonical_id, tested.ingredient_ids) != (
            administered.identity_version, administered.canonical_id, administered.ingredient_ids):
        _fail('antimicrobial_identity_mismatch')
    st, dt, ut = sf.collected, df.administered, uf.report.available
    sr, dr, ur = _range(st), _range(dt), _range(ut)
    ds, du = _relation(dr, sr), _relation(dr, ur)
    executed = instant(request.executed_at)
    if executed < max(sr[1], dr[1], ur[1]):
        _fail('invalid_execution_time')
    for item in selected:
        fact = item.fact
        recorded = (fact.provenance.recorded_at, fact.binding.verification.assessed_at,
                    fact.time.recorded, fact.time.retrieved, fact.time.processed)
        if any(executed < instant(t) for t in recorded if t is not None):
            _fail('invalid_execution_time')
    statement = (f'The selected antimicrobial administration was recorded {_time_text(dt)}. '
        f'The selected specimen was collected {_time_text(st)}. '
        f'The selected susceptibility revision was recorded as available {_time_text(ut)}. '
        f'Administration occurred {ds} specimen collection and {du} susceptibility availability.')
    uncertainty = list(MANDATORY_UNCERTAINTY)
    for role, item in zip(('S', 'I', 'U', 'D'), selected, strict=True):
        uncertainty.append(f'Selected {role} canonical digest: {item.expected_digest}.')
        uncertainty.append(f'Selected {role} verification: {item.fact.verification}; conflict: {item.fact.conflict}; provenance: {item.fact.provenance.lineage}.')
        for text in item.disclosures + item.fact.disclosures + item.fact.uncertainty + item.fact.provenance.limitations:
            uncertainty.append(f'Selected {role} source limitation: {text}')
    for role, agent in (('U', tested), ('D', administered)):
        for text in agent.mapping_provenance.limitations:
            uncertainty.append(f'Selected {role} identity mapping limitation: {text}')
    for fact, role in ((inf, 'specimen'), (uf, 'isolate')):
        binding = next(b for b in fact.domain_bindings if b.role == role)
        for text in binding.provenance.limitations:
            uncertainty.append(f'Selected {role} binding limitation: {text}')
    for role, time in (('S',st), ('U',ut), ('D',dt)):
        if time.uncertainty:
            uncertainty.append(f'Selected {role} time uncertainty: {time.uncertainty}')
    uncertainty = tuple(dict.fromkeys(uncertainty))
    if len(uncertainty) > 512 or sum(len(t) for t in uncertainty) > 65536:
        _fail('evidence_limits_exceeded')
    inputs = tuple(item.reference for item in selected)
    result = ClinicalInference(id=request.inference_id, revision=request.revision,
        binding=sf.binding, origin='inferred', inputs=inputs, method=METHOD,
        statement=statement, applicability=APPLICABILITY, uncertainty=uncertainty,
        validation_limitations=VALIDATION_LIMITATION, supersedes=request.supersedes,
        correction_reason=request.correction_reason,
        provenance=Provenance(source=Source(namespace='clinrx.synthetic', identifier=METHOD.id, version='1', channel='system'),
            actor=METHOD.id + '/v1', recorded_at=request.executed_at,
            upstream=tuple(LineageEdge(target=ref, relationship='derived_from') for ref in inputs),
            lineage='complete', limitations=('Exactly four selected direct dependencies; source authenticity and complete ancestry are not established.',)),
        time=ClinicalTime(event=request.executed_at, recorded=request.executed_at, processed=request.executed_at, precision='instant'),
        verification='unverified', conflict='unknown', temporal_status='unknown')
    canonical_payload(result)
    return result


def build_micro_antimicrobial_timing_inference(*, assembly: PatientStateAssemblyResultV2,
        request: MicroAntimicrobialTimingRequest) -> ClinicalInference:
    """Consume only supplied evidence and explicit execution time; no I/O or clocks.

    Displayed errors are bounded. Traceback locals are not a privacy boundary.
    """
    try:
        if type(request) is not MicroAntimicrobialTimingRequest:
            raise ValueError('wrong request type')
        request = MicroAntimicrobialTimingRequest.model_validate(request)
    except Exception:
        raise MicroAntimicrobialInferenceError('invalid_request') from None
    try:
        return _build(assembly, request)
    except MicroAntimicrobialInferenceError:
        raise
    except Exception:
        raise MicroAntimicrobialInferenceError('invalid_assembly') from None
