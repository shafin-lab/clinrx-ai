"""Opt-in RF1 composition. One cutoff and shared accounting; no writes/inference."""
from app.api.review_commands import _Envelope, InvalidStateContext
from app.api.schemas.circulatory import CirculatoryStateContext, CirculatoryStateResponse
from app.api.schemas.renal_fluid import (CONCEPT, RenalObservation, RenalObservations,
    RenalFluidContext, RenalFluidResponse, RenalHistoryResponse, digest)
from app.execution.patient_state_v3 import PatientStateScopeV3
from app.execution.patient_state_v3_assembly import AssemblyRequestV3, _assemble
from app.models.clinical.facts import ClinicalObservation
from app.persistence.bounded_history import HistoryBudget, AggregateHistoryBudget, HistoryAccounting
from app.persistence.canonical import canonical_payload
from app.persistence.errors import RecordNotFound, StorageIntegrityError, QueryLimitExceeded, UnsupportedOperation
from app.persistence.history import FactIdentity
from app.persistence.repository import transaction
from app.services.circulatory_product_service import CirculatoryProductService

class RenalFluidProductService(CirculatoryProductService):
    def __init__(self, dependencies, *, history_budget=None, aggregate_budget=None, max_observations=128):
        super().__init__(dependencies)
        self.history_budget = history_budget or HistoryBudget()
        self.aggregate_budget = aggregate_budget or AggregateHistoryBudget()
        self.max_observations = min(max_observations, 128)
        self.codec = _Envelope(dependencies.config.envelope_signing_key, 'synthetic-renal-fluid-context', RenalFluidContext, InvalidStateContext)

    @staticmethod
    def placement(fact, scope):
        # Legacy event is NOT specimen collection time; no fallback to recorded time.
        at = fact.time.event
        if at is None or fact.time.precision != 'instant':
            return 'unplaced'
        return 'in_window' if scope.review_start <= at <= scope.review_end else 'outside_window'

    def item(self, stored, scope):
        return RenalObservation(fact=stored.fact, expected_digest=digest(stored.fact),
            canonical_fact=canonical_payload(stored.fact), ingestion=stored.ingestion,
            inclusion=self.placement(stored.fact, scope))

    def build(self, repo, scope, accounting):
        request = AssemblyRequestV3(scope=scope)
        assembly = _assemble(repo, request, history_budget=self.history_budget, accounting=accounting)
        # Raw history, not the v1 clinical-time projection: missing/unplaced records survive.
        history = repo.list_bounded_history(target=scope.target, cutoff=scope.repository_cutoff,
            budget=self.history_budget, accounting=accounting)
        terminal = {}
        for stored in history.records:
            terminal[(stored.fact.kind, stored.fact.id)] = stored
        observations = tuple(self.item(s, scope) for key, s in sorted(terminal.items())
            if isinstance(s.fact, ClinicalObservation) and s.fact.concept_id == CONCEPT)
        if len(observations) > self.max_observations:
            raise QueryLimitExceeded('renal observation limit exceeded')
        laboratory = RenalObservations(scope=scope, observations=observations)
        c = CirculatoryStateContext(assembly_request=request, assembly_digest=assembly.canonical_digest)
        circulatory = CirculatoryStateResponse(**c.model_dump(), assembly=assembly,
            state_context=self.dependencies.state_context.issue(c), execution_enabled=False)
        context = RenalFluidContext(scope=scope, circulatory_digest=assembly.canonical_digest,
            observations_digest=digest(laboratory))
        return self.bounded(RenalFluidResponse(context=context, state_context=self.codec.issue(context),
            circulatory=circulatory, laboratory=laboratory, canonical_assembly=canonical_payload(assembly),
            canonical_laboratory=canonical_payload(laboratory)))

    def require_closed(self):
        if self.dependencies.config.circulatory_execution_enabled:
            raise UnsupportedOperation('RF1 requires disabled execution')

    def state(self, patient_id, encounter_id, start, end):
        self.require_closed()
        target = self.scope(patient_id, encounter_id)
        self.window(start, end)
        with transaction(self.dependencies.engine) as repo:
            repo.load_patient(patient_id)
            repo.load_encounter(patient_id=patient_id, encounter_id=encounter_id)
            scope = PatientStateScopeV3(patient_id=target.patient_id, encounter_id=target.encounter_id,
                review_start=start, review_end=end, repository_cutoff=repo.capture_cutoff())
            return self.build(repo, scope, HistoryAccounting(self.aggregate_budget))

    def history(self, patient_id, encounter_id, body):
        self.require_closed()
        context = self.codec.verify(body.state_context)
        self.require_scope(context.scope.target, patient_id, encounter_id)
        self.window(context.scope.review_start, context.scope.review_end)
        if body.reference.kind != 'observation':
            raise RecordNotFound('resource not found')
        with transaction(self.dependencies.engine) as repo:
            accounting = HistoryAccounting(self.aggregate_budget)
            current = self.build(repo, context.scope, accounting)
            if current.context != context:
                raise StorageIntegrityError('historical composite differs from signed context')
            if not any(i.fact.reference.model_dump() == body.reference.model_dump() for i in current.laboratory.observations):
                raise RecordNotFound('resource not found')
            history = repo.list_bounded_history(target=context.scope.target, cutoff=context.scope.repository_cutoff,
                identity=FactIdentity(kind=body.reference.kind, id=body.reference.id),
                budget=HistoryBudget(max_rows=128), accounting=accounting)
            if any(not isinstance(s.fact, ClinicalObservation) or s.fact.concept_id != CONCEPT for s in history.records):
                raise StorageIntegrityError('history outside allowed observation concept')
            return self.bounded(RenalHistoryResponse(context=context, reference=body.reference,
                revisions=tuple(self.item(s, context.scope) for s in history.records)))
