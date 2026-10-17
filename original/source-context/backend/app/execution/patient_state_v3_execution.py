"""M7-B supplied protected evidence contracts; no reads, clocks or commit claims."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, ValidationError, field_validator, model_validator

from app.execution.patient_state_v3 import PatientStateScopeV3 as PatientStateScope, RetainedStateItemV3 as RetainedStateItem
from app.execution.patient_state_v3_assembly import AssemblyRequestV3
from app.models.clinical.hemodynamics import CirculatoryRecord
from app.execution.patient_state_v3_inference import METHOD, CirculatoryTimingRequest
from app.models.clinical.common import DomainModel, LineageEdge, Reference, Text
from app.models.clinical.facts import ClinicalInference, ClinicalObservation, MedicationAdministration, MedicationOrder
from app.models.clinical.governance import Digest, GovernancePolicy, DependencyRequirement, OutputTarget, ReleaseDecision, ValidityWindow
from app.persistence.errors import PersistenceInputError, RecordConflict, UnsupportedOperation
from app.persistence.mapping import canonical_payload
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff


def ref(kind, name):
    return Reference(kind=kind, id=name, version='1')


WORKFLOW = 'SyntheticCirculatoryProtectedExecution/v1'
PROFILE = 'RecordedCirculatoryEvidence:1'
IMPLEMENTATION = ref('software', 'CirculatoryExecutionContract')
RECHECK_POLICY = ref('final_recheck_policy', 'CirculatoryFinalRecheck')
RECHECK_IMPLEMENTATION = ref('software', 'CirculatoryFinalRecheck')
USE = ref('intended_use', 'SyntheticCirculatoryReview')
SAFETY = ref('safety_policy', 'SyntheticCirculatorySafety')
FIDELITY = ref('content_validation_method', 'SyntheticCirculatoryFidelity')
FRESHNESS = ref('freshness_policy', 'SyntheticCirculatoryFinalContext')
AUTHORIZATION = ref('authorization_policy', 'SyntheticCirculatoryReleaseGrant')
RULES = (ref('safety_rule', 'circulatory_exact_selected_evidence'),
         ref('safety_rule', 'circulatory_protected_terminal_suitability'),
         ref('safety_rule', 'circulatory_bounded_descriptive_content'))
FINAL_ASSESSOR = 'SyntheticCirculatoryFinalContext/v1'
FIDELITY_ASSESSOR = 'SyntheticCirculatoryFidelity/v1'
GRANT_ACTOR = 'synthetic-circulatory-orchestrator'
GRANT_ISSUER = 'SyntheticCirculatoryReleaseIssuer/v1'
GRANT_TARGET = OutputTarget(context={'patient_id':'synthetic-p1', 'encounter_id':'synthetic-e1'},
    request_id='synthetic-circulatory-request', intended_use=USE,
    destination='synthetic-circulatory-local', recipient='synthetic-circulatory-reviewer')
GRANT_WINDOW = ValidityWindow(start=datetime(2026, 10, 8, 12, tzinfo=timezone.utc),
                              end=datetime(2026, 10, 8, 12, 5, tzinfo=timezone.utc))
LIMITATIONS = (
    'Synthetic explicit-subset temporal review only; no patient-care authorization or delivery.',
    'Only exact selected P/L/V and explicit supporting evidence is assessed; unsupported domains do not establish clinical absence.',
    'Source completeness and authenticity are not established; availability by review end is not asserted.',
    'No diagnosis, causal attribution, medication-effect assessment or treatment recommendation.',
    'Direct selected dependencies only; complete upstream ancestry is not established.',
)


class CirculatoryExecutionError(Exception):
    """Bounded validation boundary; no clinical payloads in displayed messages."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code='invalid_contract'):
    if not condition:
        raise CirculatoryExecutionError(code)


def digest(value):
    return sha256(canonical_payload(value).encode('utf-8')).hexdigest()


def same(a, b):
    return canonical_payload(a) == canonical_payload(b)


def instant(value):
    # Integer UTC axis preserves actual instants, including offset/DST boundaries.
    offset = value.utcoffset()
    require(offset is not None, 'invalid_time')
    return (((value.toordinal()*24+value.hour)*60+value.minute)*60+value.second)*1_000_000+value.microsecond - (
        (offset.days*86400+offset.seconds)*1_000_000+offset.microseconds)


def storage(value):
    if isinstance(value, (RepositoryCutoff, IngestionMetadata)):
        value = value.model_dump(warnings=False)
    if isinstance(value, dict) and 'payload_version' in value:
        require(type(value['payload_version']) is int, 'invalid_metadata')
    return value


class ProtectedContract(DomainModel):
    @model_validator(mode='wrap')
    @classmethod
    def bounded_validation(cls, value, handler):
        try:
            return handler(value)
        except (ValidationError, ValueError, TypeError, PersistenceInputError, UnsupportedOperation):
            raise CirculatoryExecutionError('invalid_contract') from None


class CirculatoryExecutionRequest(ProtectedContract):
    """Requires an already persisted original inference; this model proves no I/O."""
    execution_id: UUID
    target: OutputTarget
    actor: Text
    inference_request: CirculatoryTimingRequest
    assembly_request: AssemblyRequestV3
    inference_cutoff: RepositoryCutoff
    expected_inference_digest: Digest
    requested_at: AwareDatetime
    workflow: Literal['SyntheticCirculatoryProtectedExecution/v1'] = WORKFLOW
    profile: Literal['RecordedCirculatoryEvidence:1'] = PROFILE

    _cutoff = field_validator('inference_cutoff', mode='before')(storage)

    @property
    def inference_reference(self):
        return Reference(kind='inference', id=self.inference_request.inference_id, version=self.inference_request.revision)

    @property
    def pins(self):
        return self.inference_request.pins

    @property
    def inputs(self):
        return self.inference_request.inputs

    @model_validator(mode='after')
    def coherent(self):
        scope=self.inference_request.scope
        require(self.target.context==scope.target and self.target.intended_use==USE,'invalid_scope')
        require(same(self.assembly_request.scope,scope),'invalid_scope')
        require(self.inference_cutoff.repository_id==scope.repository_cutoff.repository_id
            and self.inference_cutoff.fact_watermark>scope.repository_cutoff.fact_watermark,'invalid_inference_prefix')
        require(instant(self.requested_at)>=instant(self.inference_request.executed_at),'invalid_request_time')
        canonical_payload(self)
        return self


class CirculatoryEvidenceWitness(ProtectedContract):
    role: Literal['P', 'L', 'V', 'support']
    consumed: Reference
    item_digest: Digest
    source_digest: Digest
    original_ingestion: IngestionMetadata
    terminal: Reference
    terminal_source_digest: Digest
    terminal_ingestion: IngestionMetadata
    suitability: Literal['established', 'failed', 'unavailable']

    _metadata = field_validator('original_ingestion', 'terminal_ingestion', mode='before')(storage)

    @property
    def status(self):
        return 'current' if self.consumed == self.terminal else 'superseded'

    @model_validator(mode='after')
    def coherent(self):
        require((self.terminal.kind,self.terminal.id)==(self.consumed.kind,self.consumed.id),'invalid_terminal_identity')
        require(self.original_ingestion.repository_id == self.terminal_ingestion.repository_id, 'invalid_metadata')
        if self.status == 'current':
            require(self.source_digest == self.terminal_source_digest and same(self.original_ingestion, self.terminal_ingestion), 'contradictory_exact_evidence')
        else:
            require(self.terminal_ingestion.ingestion_sequence > self.original_ingestion.ingestion_sequence, 'invalid_successor')
        return self


class CirculatoryInferenceWitness(ProtectedContract):
    reference: Reference
    expected_digest: Digest
    observed_digest: Digest
    ingestion: IngestionMetadata
    terminal: Reference
    terminal_digest: Digest
    terminal_ingestion: IngestionMetadata
    method: Reference
    inputs: tuple[Reference, ...]
    dependencies: tuple[Reference, ...]
    declarations: tuple[LineageEdge, ...]
    reconstruction_digest: Digest | None

    _metadata = field_validator('ingestion', 'terminal_ingestion', mode='before')(storage)

    @property
    def status(self):
        return 'current' if self.reference == self.terminal else 'superseded'

    @property
    def reconstruction(self):
        return ('unavailable' if self.reconstruction_digest is None else
                'matched' if self.reconstruction_digest == self.observed_digest else 'mismatch')

    @model_validator(mode='after')
    def coherent(self):
        require(self.reference.kind == 'inference' and self.method == METHOD, 'invalid_inference_identity')
        require(self.expected_digest == self.observed_digest, 'original_inference_mismatch')
        require((self.terminal.kind, self.terminal.id) == (self.reference.kind, self.reference.id), 'invalid_terminal_identity')
        require(self.inputs == self.dependencies and self.declarations == tuple(
            LineageEdge(target=r, relationship='derived_from') for r in self.inputs), 'invalid_dependencies')
        require(3 <= len(set(self.inputs)) == len(self.inputs) <= 35, 'invalid_dependencies')
        require(self.ingestion.repository_id == self.terminal_ingestion.repository_id, 'invalid_metadata')
        if self.status == 'current':
            require(self.observed_digest == self.terminal_digest and same(self.ingestion, self.terminal_ingestion), 'contradictory_exact_evidence')
        else:
            require(self.terminal_ingestion.ingestion_sequence > self.ingestion.ingestion_sequence, 'invalid_successor')
        return self


class CirculatoryFinalRecheck(ProtectedContract):
    scope: PatientStateScope
    inference_cutoff: RepositoryCutoff
    final_cutoff: RepositoryCutoff
    evidence: tuple[CirculatoryEvidenceWitness, ...]
    terminal_facts: tuple[CirculatoryRecord, ...]
    inference: CirculatoryInferenceWitness

    _metadata=field_validator('inference_cutoff','final_cutoff',mode='before')(storage)

    @property
    def outcome(self):
        if any(w.status=='superseded' for w in self.evidence) or self.inference.status=='superseded':
            return 'materially_changed'
        return 'unchanged' if self.inference.reconstruction=='matched' else 'unavailable'

    @property
    def reasons(self):
        result=tuple('selected_evidence_superseded:'+str(i) for i,w in enumerate(self.evidence) if w.status=='superseded')
        if self.inference.status=='superseded': result+=('inference_superseded',)
        if self.inference.reconstruction!='matched': result+=('reconstruction_unavailable',)
        return result

    @model_validator(mode='after')
    def coherent(self):
        require(3<=len(self.evidence)<=35 and len(self.evidence)==len(self.terminal_facts),'invalid_witnesses')
        require(tuple(w.role for w in self.evidence)==('P','L','V')+('support',)*(len(self.evidence)-3),'invalid_witness_roles')
        original=self.scope.repository_cutoff
        require(original.repository_id==self.inference_cutoff.repository_id==self.final_cutoff.repository_id,'invalid_repository')
        require(original.fact_watermark<self.inference_cutoff.fact_watermark<=self.final_cutoff.fact_watermark,'invalid_prefix')
        refs=tuple(w.consumed for w in self.evidence)
        require(refs==self.inference.inputs and len(set(refs))==len(refs),'invalid_dependencies')
        for fact,w in zip(self.terminal_facts,self.evidence,strict=True):
            require(fact.reference==w.terminal and digest(fact)==w.terminal_source_digest
                and fact.binding.target==self.scope.target,'invalid_terminal_content')
            require(w.item_digest==w.source_digest,'invalid_original_content')
            require(w.original_ingestion.repository_id==original.repository_id
                and w.original_ingestion.ingestion_sequence<=original.fact_watermark
                and w.terminal_ingestion.ingestion_sequence<=self.final_cutoff.fact_watermark,'invalid_metadata')
        i=self.inference
        require(i.ingestion.repository_id==original.repository_id
            and original.fact_watermark<i.ingestion.ingestion_sequence<=self.inference_cutoff.fact_watermark
            and i.terminal_ingestion.ingestion_sequence<=self.final_cutoff.fact_watermark,'invalid_inference_prefix')
        return self


def validate_recheck_request(request, recheck):
    request = CirculatoryExecutionRequest.model_validate(request)
    recheck = CirculatoryFinalRecheck.model_validate(recheck)
    require(same(request.inference_request.scope, recheck.scope) and same(request.inference_cutoff, recheck.inference_cutoff), 'request_recheck_mismatch')
    require(tuple(w.consumed for w in recheck.evidence) == request.inputs
            and tuple(w.item_digest for w in recheck.evidence) == tuple(p.expected_digest for p in request.pins)
            and recheck.inference.reference == request.inference_reference
            and recheck.inference.expected_digest == request.expected_inference_digest, 'request_recheck_mismatch')
    return recheck


class CirculatoryEvidence(ProtectedContract):
    request: CirculatoryExecutionRequest
    items: tuple[RetainedStateItem, ...]
    facts: tuple[CirculatoryRecord, ...]
    inference: ClinicalInference
    inference_ingestion: IngestionMetadata

    _metadata = field_validator('inference_ingestion', mode='before')(storage)

    @model_validator(mode='after')
    def coherent(self):
        r, i = self.request, self.inference
        require(tuple(x.reference for x in self.items) == r.inputs == tuple(f.reference for f in self.facts), 'invalid_evidence_order')
        require(tuple(x.expected_digest for x in self.items) == tuple(p.expected_digest for p in r.pins), 'selected_content_mismatch')
        for item, fact in zip(self.items,self.facts,strict=True):
            require(same(item.fact,fact) and fact.binding.target == r.target.context, 'source_item_mismatch')
            require(fact.binding.verification.status == 'verified', 'unverified_admission')
            require(item.ingestion is not None and item.ingestion.repository_id == r.inference_cutoff.repository_id
                    and item.ingestion.ingestion_sequence <= r.inference_request.scope.repository_cutoff.fact_watermark, 'invalid_prefix')
        require(i.binding.verification.status == 'verified' and same(i.binding,self.facts[0].binding), 'unverified_admission')
        require(i.reference == r.inference_reference and i.method == METHOD and digest(i) == r.expected_inference_digest, 'original_inference_mismatch')
        require(i.inputs == r.inputs == i.provenance.dependencies and i.provenance.upstream == tuple(
            LineageEdge(target=x,relationship='derived_from') for x in r.inputs), 'invalid_dependencies')
        require(self.inference_ingestion.repository_id == r.inference_cutoff.repository_id
                and r.inference_request.scope.repository_cutoff.fact_watermark < self.inference_ingestion.ingestion_sequence <= r.inference_cutoff.fact_watermark, 'invalid_inference_prefix')
        require(len({x.ingestion.ingestion_sequence for x in self.items}) == len(r.inputs), 'contradictory_ingestion_identity')
        return self


def validate_evidence_recheck(evidence, recheck):
    evidence = CirculatoryEvidence.model_validate(evidence)
    recheck = validate_recheck_request(evidence.request,recheck)
    for w, item, fact in zip(recheck.evidence,evidence.items,evidence.facts,strict=True):
        require(w.source_digest == digest(fact) and same(w.original_ingestion,item.ingestion), 'evidence_recheck_mismatch')
    require(same(recheck.inference.ingestion,evidence.inference_ingestion), 'evidence_recheck_mismatch')
    return evidence, recheck


def circulatory_policy(snapshot):
    facts = (*snapshot.facts[0].inputs, snapshot.facts[0].reference)
    policy = GovernancePolicy(reference=ref('governance_policy','SyntheticCirculatoryRelease'), intended_use=USE,
        safety_policy=SAFETY,freshness_policy=FRESHNESS,authorization_policy=AUTHORIZATION,content_validation_method=FIDELITY,
        required_rules=RULES,required_context=(snapshot.reference,*facts),
        required_dependencies=tuple(DependencyRequirement(reference=r,updates_required=False) for r in (*facts,METHOD,FIDELITY,*RULES)),
        max_assessment_age=timedelta(seconds=30))
    return GovernancePolicy.model_validate({**policy.model_dump(),'reference':ref('governance_policy','SyntheticCirculatoryRelease/'+digest(policy))})


def presentation_limitations(inference):
    # Retained disclosure projection only, not clinical reconstruction.
    return tuple(dict.fromkeys((*LIMITATIONS, inference.applicability, inference.validation_limitations,
                                *inference.provenance.limitations, *inference.uncertainty)))


def freshness_binding(recheck):
    return 'original='+digest(recheck.scope.repository_cutoff)+'; inference_cutoff='+digest(recheck.inference_cutoff)+'; final='+digest(recheck.final_cutoff)+'; recheck='+digest(recheck)+'; inference='+recheck.inference.observed_digest+'; outcome='+recheck.outcome


class CirculatoryRuntime(ProtectedContract):
    started_at: AwareDatetime
    observed_at: AwareDatetime
    decision_at: AwareDatetime
    finalized_at: AwareDatetime

    @model_validator(mode='after')
    def coherent(self):
        times = (self.started_at,self.observed_at,self.decision_at,self.finalized_at)
        require(all(instant(a)<=instant(b) for a,b in zip(times,times[1:])), 'invalid_runtime_chronology')
        require(all(t.utcoffset()==timedelta(0) for t in times), 'runtime_requires_utc')
        return self


class CirculatoryExecutionRecord(ProtectedContract):
    request: CirculatoryExecutionRequest
    final_recheck: CirculatoryFinalRecheck
    evidence: CirculatoryEvidence
    context_digest: Digest
    decision: ReleaseDecision
    runtime: CirculatoryRuntime
    implementation: Reference = IMPLEMENTATION
    payload_version: Literal[1] = 1

    @field_validator('payload_version',mode='before')
    @classmethod
    def exact_version(cls,value):
        require(type(value) is int and value == 1, 'invalid_payload_version')
        return value

    @property
    def disposition(self):
        return 'completed_'+self.decision.outcome

    @model_validator(mode='after')
    def coherent(self):
        # Retained structural validation only: no inference/safety/authority producer.
        require(self.implementation == IMPLEMENTATION, 'incompatible_workflow')
        r, c = self.request, validate_recheck_request(self.request,self.final_recheck)
        require(c.inference.reconstruction == 'matched', 'original_inference_mismatch')
        d, t = self.decision,self.runtime
        a = d.assessment
        snapshot = a.review.candidate.snapshot
        require(d.actor == r.actor and a.target == r.target and a.assessor == WORKFLOW, 'decision_request_mismatch')
        require(digest(snapshot) == self.context_digest and snapshot.binding.target == r.target.context, 'context_mismatch')
        require(same(self.evidence.request,r), 'context_mismatch')
        validate_evidence_recheck(self.evidence,c)
        require(len(snapshot.facts)==1 and same(snapshot.facts[0],self.evidence.inference), 'context_mismatch')
        require(snapshot.completeness == 'partial' and snapshot.limitations == LIMITATIONS and not snapshot.lineage_nodes
                and snapshot.completeness_scope == 'Exact original P/L/V and explicit supporting and inference only; request='+digest(r)+'.', 'context_mismatch')
        require(snapshot.sources == tuple(dict.fromkeys(f.provenance.source for f in snapshot.facts)), 'context_mismatch')
        for fact,w in zip(self.evidence.facts,c.evidence,strict=True):
            require(digest(fact) == w.source_digest, 'context_mismatch')
        i = snapshot.facts[-1]
        require(isinstance(i,ClinicalInference) and digest(i) == r.expected_inference_digest
                and i.method == METHOD and i.inputs == r.inputs == i.provenance.dependencies
                and i.provenance.upstream == c.inference.declarations, 'context_mismatch')
        require(same(snapshot.binding,i.binding), 'context_mismatch')
        require(i.supersedes is None and i.correction_reason is None
                and all(v is not None and v.isoformat() == r.inference_request.executed_at.isoformat()
                        for v in (i.time.event,i.time.recorded,i.time.processed,i.provenance.recorded_at)), 'context_mismatch')
        # Validate the retained policy directly; decoding must not invoke its producer.
        policy = a.policy
        facts = (*snapshot.facts[0].inputs, snapshot.facts[0].reference)
        require(policy.intended_use == USE and policy.safety_policy == SAFETY
                and policy.freshness_policy == FRESHNESS and policy.authorization_policy == AUTHORIZATION
                and policy.content_validation_method == FIDELITY and policy.required_rules == RULES
                and policy.required_context == (snapshot.reference,*facts)
                and tuple(x.reference for x in policy.required_dependencies) == (*facts,METHOD,FIDELITY,*RULES)
                and all(not x.updates_required for x in policy.required_dependencies)
                and not policy.warning_rules and policy.degraded_mode is None and not policy.degraded_dependencies
                and policy.max_assessment_age == timedelta(seconds=30) and not a.exceptions, 'policy_mismatch')
        policy_identity_payload = policy.model_copy(update={
            'reference':ref('governance_policy','SyntheticCirculatoryRelease')})
        require(policy.reference == ref('governance_policy',
                'SyntheticCirculatoryRelease/'+digest(policy_identity_payload)), 'policy_mismatch')
        require(instant(r.requested_at)<=instant(t.started_at) and d.at == t.decision_at and a.assessed_at == t.decision_at, 'invalid_runtime_chronology')
        review, state, validation = a.review,a.state,a.content_validation
        require(review.rendering is not None and len(review.evaluations)==1, 'invalid_assertions')
        evaluation = review.evaluations[0]
        require(evaluation.policy == SAFETY and tuple(x.rule for x in evaluation.checks)==RULES
                and all(x.required and not x.overrideable for x in evaluation.checks), 'invalid_assertions')
        require(validation.method == FIDELITY and validation.assessor == FIDELITY_ASSESSOR
                and validation.target == r.target and validation.content_digest == digest(review)
                and validation.payload_digest == digest(a.payload) and validation.limitations == presentation_limitations(i)
                and evaluation.limitations == presentation_limitations(i), 'invalid_assertions')
        freshness = state.freshness
        require(freshness.assessor == FINAL_ASSESSOR and freshness.policy == FRESHNESS and freshness.snapshot == snapshot.reference
                and freshness.rationale == freshness_binding(c) and freshness.adequate == (c.outcome=='unchanged')
                and freshness.material_change == (c.outcome=='materially_changed'), 'invalid_freshness')
        refs = (snapshot.reference,*r.inputs,r.inference_reference)
        require(tuple(x.reference for x in freshness.items)==refs, 'invalid_freshness')
        expected_state = 'fresh' if c.outcome=='unchanged' else 'stale' if c.outcome=='materially_changed' else 'unknown'
        require(all(x.state==expected_state and (x.validity is not None)==(c.outcome=='unchanged') for x in freshness.items), 'invalid_freshness')
        require(tuple(x.reference for x in state.dependencies)==tuple(x.reference for x in a.policy.required_dependencies), 'invalid_assertions')
        require(state.target == r.target and same(state.identity,snapshot.binding.verification), 'invalid_assertions')
        auth = state.authorization
        require(auth.policy == AUTHORIZATION and auth.issuer == GRANT_ISSUER and auth.subject == r.actor
                and auth.action == 'release' and auth.role == 'synthetic-circulatory-reviewer' and same(auth.validity,GRANT_WINDOW)
                and auth.target == r.target and auth.content_digest == digest(review)
                and auth.payload_digest == digest(a.payload) and auth.governance_policy_digest == digest(a.policy), 'invalid_authority_binding')
        observed = (snapshot.created_at,snapshot.temporal_cutoff,review.candidate.created_at,review.rendering.rendered_at,
                    evaluation.evaluated_at,validation.assessed_at,freshness.assessed_at,state.observed_at)
        require(all(v==t.observed_at for v in observed) and auth.issued_at==t.decision_at, 'invalid_runtime_chronology')
        require(c.outcome=='unchanged' or d.outcome=='withheld', 'invalid_disposition')
        if d.outcome == 'released':
            require(len(review.candidate.claims)==1 and review.rendering.content==i.statement
                    and review.candidate.claims[0].action==i.statement
                    and review.candidate.claims[0].basis==(i.reference,)
                    and review.candidate.claims[0].conditions==(i.applicability,)
                    and review.candidate.claims[0].uncertainty==i.uncertainty
                    and review.candidate.claims[0].warnings==(i.validation_limitations,*i.provenance.limitations), 'released_content_mismatch')
        canonical_payload(self)
        return self


def circulatory_request_projection(value):
    if isinstance(value,CirculatoryExecutionRecord):
        value = CirculatoryExecutionRecord.model_validate(value).request
    else:
        require(type(value) is CirculatoryExecutionRequest, 'invalid_request')
        value = CirculatoryExecutionRequest.model_validate(value)
    return canonical_payload(value)


def require_circulatory_request_match(retained, request):
    """No lookup: future retry and reconciliation share this exact matcher."""
    left = circulatory_request_projection(retained)
    right = circulatory_request_projection(request)
    if left != right:
        raise RecordConflict('execution identity has a different request or workflow')
