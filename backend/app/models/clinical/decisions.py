"""Candidate/evaluation records only. No clinical release engine is implemented."""
from enum import Enum
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from .common import (DomainModel, Provenance, Reference, Text,
                     ensure_consistent_revisions, require_kind)
from .facts import ContextSnapshot


class KnowledgeReference(DomainModel):
    kind: Literal['knowledge'] = 'knowledge'
    id: Text
    version: Text
    applicability: Text


class EvidenceReference(DomainModel):
    kind: Literal['evidence'] = 'evidence'
    id: Text
    version: Text  # Internal assessed revision; external source version may be unknown.
    source_version: Text | None = None
    citation: Text
    locator: Text
    retrieved_at: AwareDatetime
    retained_snapshot: Reference | None = None
    recovery_limitation: Text | None = None

    @model_validator(mode='after')
    def recovery_is_explicit(self):
        if self.retained_snapshot:
            require_kind(self.retained_snapshot, 'source_snapshot')
        if not self.retained_snapshot and not self.recovery_limitation:
            raise ValueError('citation alone does not establish recoverability')
        return self


class RecommendationState(str, Enum):
    CANDIDATE = 'candidate'
    RENDERED = 'rendered'
    EVALUATED = 'evaluated'
    RELEASED = 'released'
    PRESENTED = 'presented'
    WITHHELD = 'withheld'


class ClinicalClaim(DomainModel):
    id: Text
    action: Text
    rationale: Text
    classifications: Annotated[tuple[Literal['deterministic', 'rule_derived', 'evidence_derived', 'ai_inferred'], ...],
                               Field(min_length=1)]
    basis: Annotated[tuple[Reference, ...], Field(min_length=1)]
    conditions: tuple[Text, ...] = ()
    warnings: tuple[Text, ...] = ()
    uncertainty: tuple[Text, ...] = ()


class ClinicalRecommendation(DomainModel):
    id: Text
    revision: Text
    snapshot: ContextSnapshot
    intended_use: Reference
    claims: Annotated[tuple[ClinicalClaim, ...], Field(min_length=1)]
    knowledge: tuple[KnowledgeReference, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()
    alternatives: tuple[Text, ...] = ()
    monitoring: tuple[Text, ...] = ()
    limitations: tuple[Text, ...] = ()
    provenance: Provenance
    created_at: AwareDatetime
    state: Literal['candidate'] = 'candidate'

    @property
    def reference(self):
        return Reference(kind='recommendation', id=self.id, version=self.revision)

    @model_validator(mode='after')
    def candidate_integrity(self):
        ensure_consistent_revisions(
            (Reference(kind=item.kind, id=item.id, version=item.version), item)
            for item in (*self.knowledge, *self.evidence)
        )
        if self.created_at < self.snapshot.created_at:
            raise ValueError('recommendation cannot precede its snapshot')
        if len({c.id for c in self.claims}) != len(self.claims):
            raise ValueError('claim identities must be unique')
        if self.intended_use.kind != 'intended_use':
            raise ValueError('intended use must identify its versioned specification')
        return self


class RenderedRecommendation(DomainModel):
    id: Text
    revision: Text
    candidate: Reference
    snapshot: Reference
    content: Text
    destination: Text
    rendered_at: AwareDatetime

    @property
    def reference(self):
        return Reference(kind='rendering', id=self.id, version=self.revision)

    @model_validator(mode='after')
    def reference_kinds(self):
        require_kind(self.candidate, 'recommendation')
        require_kind(self.snapshot, 'snapshot')
        return self


class SafetyCheck(DomainModel):
    id: Text
    rule: Reference
    required: StrictBool
    outcome: Literal['no_detected_violation', 'warning', 'hard_failure', 'unavailable', 'not_applicable']
    reason: Text
    coverage: Text
    overrideable: StrictBool = False

    @model_validator(mode='after')
    def only_warnings_allow_exception(self):
        require_kind(self.rule, 'safety_rule')
        if self.overrideable and self.outcome != 'warning':
            raise ValueError('only explicitly classified warnings may be overrideable')
        return self


class SafetyEvaluation(DomainModel):
    id: Text
    revision: Text
    candidate: Reference
    rendering: Reference
    snapshot: Reference
    policy: Reference
    checks: Annotated[tuple[SafetyCheck, ...], Field(min_length=1)]
    exact_meaning: Literal['matched', 'failed', 'unavailable']
    coverage: Text
    limitations: tuple[Text, ...]
    uncertainty: tuple[Text, ...] = ()
    evaluated_at: AwareDatetime

    @property
    def reference(self):
        return Reference(kind='safety_evaluation', id=self.id, version=self.revision)

    # Python-only derived property: JSON stores the underlying checked records.
    @property
    def outcome(self) -> Literal['hard_failure', 'incomplete', 'warning', 'not_applicable', 'no_detected_violation']:
        if self.exact_meaning == 'failed' or any(c.outcome == 'hard_failure' for c in self.checks):
            return 'hard_failure'
        if self.exact_meaning == 'unavailable' or any(c.outcome == 'unavailable' for c in self.checks):
            return 'incomplete'
        if any(c.outcome == 'warning' for c in self.checks):
            return 'warning'
        if all(c.outcome == 'not_applicable' for c in self.checks):
            return 'not_applicable'
        return 'no_detected_violation'

    @model_validator(mode='after')
    def unique_checks(self):
        if len({c.id for c in self.checks}) != len(self.checks):
            raise ValueError('check identities must be unique')
        expected = ((self.candidate, 'recommendation'), (self.rendering, 'rendering'),
                    (self.snapshot, 'snapshot'), (self.policy, 'safety_policy'))
        if any(ref.kind != kind for ref, kind in expected):
            raise ValueError('incorrect evaluation reference kind')
        return self


class RecommendationReview(DomainModel):
    """Consistent immutable review bundle; evaluation is not release permission."""
    candidate: ClinicalRecommendation
    rendering: RenderedRecommendation | None = None
    evaluations: tuple[SafetyEvaluation, ...] = ()

    # Python-only derived property; never accept caller-supplied release state.
    @property
    def state(self) -> RecommendationState:
        if self.evaluations:
            return RecommendationState.EVALUATED
        return RecommendationState.RENDERED if self.rendering else RecommendationState.CANDIDATE

    @model_validator(mode='after')
    def exact_references(self):
        ensure_consistent_revisions((e.reference, e) for e in self.evaluations)
        if self.evaluations and not self.rendering:
            raise ValueError('evaluation requires rendered content')
        if self.rendering:
            if (self.rendering.candidate != self.candidate.reference or
                    self.rendering.snapshot != self.candidate.snapshot.reference):
                raise ValueError('rendering must bind the exact candidate and context')
            if self.rendering.rendered_at < self.candidate.created_at:
                raise ValueError('rendering cannot precede candidate')
        for evaluation in self.evaluations:
            if (evaluation.candidate != self.candidate.reference or
                    evaluation.rendering != self.rendering.reference or
                    evaluation.snapshot != self.candidate.snapshot.reference):
                raise ValueError('evaluation must bind exact content and context revisions')
            if evaluation.evaluated_at < self.rendering.rendered_at:
                raise ValueError('evaluation cannot precede rendering')
        return self


class HumanDecision(DomainModel):
    """An attributable event, never a mutation of a safety outcome or release grant.

    Override attempts are recorded, but effective warning exceptions are deferred
    until an authority/policy evaluator exists.
    """
    id: Text
    evaluation: SafetyEvaluation
    actor: Text
    role: Text
    authority: Reference
    at: AwareDatetime
    action: Literal['review', 'acknowledge', 'accept', 'reject', 'modify', 'override_attempt']
    rationale: Text
    target_check_id: Text | None = None
    new_candidate: Reference | None = None

    @model_validator(mode='after')
    def distinct_human_action(self):
        if self.at < self.evaluation.evaluated_at:
            raise ValueError('decision cannot precede the reviewed evaluation')
        if self.action == 'override_attempt' and not self.target_check_id:
            raise ValueError('override attempt requires an exact check')
        if self.target_check_id and self.target_check_id not in {c.id for c in self.evaluation.checks}:
            raise ValueError('target check is not in the reviewed evaluation')
        if self.action == 'modify':
            if not self.new_candidate or self.new_candidate.kind != 'recommendation' or self.new_candidate == self.evaluation.candidate:
                raise ValueError('modification requires a new candidate revision')
        elif self.new_candidate:
            raise ValueError('only modification can link a replacement candidate')
        return self
