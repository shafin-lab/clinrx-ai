# Sprint 6B: core clinical model prototype

Implementation notes, not a new architecture standard. Basis: committed
CLINRX-ARCH-001 v1.1 (Sections 5–7, 10–14), CLINRX-DATA-001 v0.3
(Sections 19–40), and CLINRX-SAFE-001 v0.2 (Sections 5–15, 25, 28), at
`df1399961e504a924a77a2925c1c9b14f8541bb5`.
All three remain Draft. These contracts support synthetic development data;
they neither implement clinical validation nor authorize patient-care use.

## Modules and scope

- `common.py`: exact revision references, local content-consistency checks,
  source namespaces, clinical times, context targets and identity-verification
  assertions, quantities/units/missingness, and typed execution-lineage edges.
- `facts.py`: PatientContext, EncounterContext, seven discriminated fact categories
  (ClinicalObservation, ClinicalCondition, MedicationOrder,
  MedicationAdministration, Procedure, DerivedValue, ClinicalInference),
  minimal medication/dose structures, CalculationInput/CalculationExecution,
  and immutable ContextSnapshot.
- `decisions.py`: separate KnowledgeReference and EvidenceReference, structured
  candidate claims, exact renderings, SafetyEvaluation, RecommendationReview,
  and HumanDecision events.

These use the backend's existing Pydantic v2 dependency. RetrievalResult, its
imports, services, endpoints, and dependencies are unchanged. No persistence,
new framework, endpoint, or clinical algorithm is introduced. Slice 2 adds pure
release/presentation governance decisions without performing external actions.
Import from the owning module, e.g.
`from app.models.clinical.facts import ClinicalObservation`.

## Values, facts and medication records

Fact category, origin, verification, conflict, temporal status and missingness
remain separate. `temporal_status` describes current/historical/unknown, while
`diagnostic_status`, `order_status` and `procedure_status` carry category-specific
clinical meaning. PatientFact is a base contract, not a constructible clinical
record; misuse raises a validation error. Machine-inferred diagnoses remain
ClinicalInference. Reported measurements can be clinician confirmed without
changing origin.

ClinicalValue accepts a Quantity, text, a strict Boolean, or explicit missingness.
Bare numeric values are rejected in Python and JSON, including 0 and 1; only real
Booleans encode Boolean findings. Text remains uninterpreted text, never implicitly
parsed into a measurement or Boolean. Quantity uses finite Decimal values.
Unit retains raw source spelling independently of an explicit unresolved,
assessed or normalized status. Assessed/normalized units require a coding system
and code; unresolved units require a limitation and do not assert a resolved code.
These fields record an assessment, not proof that a code is valid or that a
conversion is clinically appropriate. There is no unit parser or converter.

MedicationIdentity distinguishes ingredient identities, product identity and
reported formulation where known. It does not infer equivalence between them.
Dose carries amount and basis, with optional concentration, volume, rate,
duration and structured frequency. Route and schedule_text retain source wording;
no terminology mapping or dimensional compatibility is implied. Cumulative
exposure is deliberately deferred to a calculation over identified administrations
and a time window, not stored as an unexplained mutable total.

Orders and actual administrations have separate contracts. Administration requires
an explicit delivered-total basis and `administered_at == time.event` (equal
instants may have different offsets). It cannot precede its actual delivery in
source/provenance recording time or occur after the snapshot cutoff. This narrow
record describes completed delivery; planned/in-progress/missed administration
and uncertain delivery intervals need later ingestion contracts. An order link
is not evidence of delivery. Source authenticity is an ingestion responsibility.
Known medication conflicts are rejected within the bundle; complementary partial
identity descriptions may coexist, without certifying product equivalence.

## Binding, temporal consistency and revisions

Binding contains a ContextTarget and a separate IdentityVerification assertion.
Reverification can change verifier, method, time or source without changing the
clinical target or rewriting earlier facts. Snapshot/fact targets must match and
both assertions must be verified by snapshot creation. Unresolved matching cannot
become a verified snapshot. Cross-encounter historical aggregation still needs a
separate reconciliation design.

Snapshots embed immutable fact revisions and reject records acquired after their
cutoff, including source recording, retrieval, processing, calculation execution,
actual administration, and supplied intermediate lineage recording. Future
planned procedure events and future effective periods remain representable;
event time is not universally equated to availability. Corrections retain the
previous revision and reason. More precise per-timestamp uncertainty/interval
profiles are deferred.

Within supplied bundles, contradictory content under the same exact reference is
rejected for calculation executions, lineage nodes, safety evaluations and
knowledge/evidence descriptors. Duplicate fact revisions are rejected outright.
Identical shared executions/descriptors are permitted. Different revisions remain
separate records. Cross-request uniqueness and conflicts against prior stored
content are persistence responsibilities; reference equality alone cannot detect
changed content when only one representation is supplied.

## Calculations

CalculationExecution pins definition, implementation, rounding policy, input
snapshot and clinical context. Configuration/environment and assumptions remain
explicit. CalculationInput names the parameter and exact fact revision, with
optional retained source/evaluated quantities and a versioned conversion reference.
Changed retained representations require conversion provenance. The same fact
may fill multiple named roles, but parameter names cannot repeat. Reference
kinds are constrained at the boundaries that distinguish facts, executions,
methods, policies and conversions; there is no universal reference registry.

Completed executions require available inputs and a final result. Retained
unresolved evaluated/result units cannot be presented as completed calculations.
A missing_input execution may have zero available inputs and must name the missing
parameters; available and missing parameter sets cannot overlap. Other failures
carry reasons and no final result. No fabricated reference is required to record
missingness. A failed execution cannot become a DerivedValue.

DerivedValue preserves calculated_from input edges, the successful execution and
matching clinical context. Its recording cannot precede execution, and a snapshot
cannot contain an execution after its cutoff. Locally present input facts cannot
postdate execution. This is structural integrity, not demonstrated mathematical
reproduction: absent input/snapshot references still require an authorized
resolver. That resolver must establish actual retained values, unit meaning,
input-snapshot membership, applicability, conversions and recovery availability.

## Lineage, copying and confirmation

Provenance edges distinguish copied_from, derived_from, calculated_from,
independent_confirmation and fulfills_order. Actor and recording time belong to
the owning provenance assertion. Fulfillment links express intended-order
association, not an independent evidentiary basis for administration.

The bounded LineageGraph checks dependency cycles and origin preservation through
supplied intermediate records; snapshots can include those records as
lineage_nodes. Copies of inferred/derived content retain that origin, including
external-note reimport. Known inferred/derived dependency paths cannot become
observed/reported facts. Source channel and inference origin remain independent.

A subsequent independent-confirmation assertion identifies its earlier target,
new observation basis and rationale. It must follow the earlier assertion when
both records are supplied; its basis must already be available. Shared ancestry
with the original assertion rejects the claim of independent confirmation. The
original inference remains inferred. The graph returns dependent or unknown,
never infers independence from different IDs, and does not certify a clinician's
assertion of independence. Hidden origin, missing external nodes or dishonest
metadata cannot be recovered by structural validation; limitations remain explicit.

## Recommendations, safety and serialization decision

ClinicalRecommendation remains a candidate. RecommendationReview derives candidate,
rendered or evaluated state from exact matching content/context records, including
failed evaluations. Slice 2 implements released, presented and withheld as
separate governance decisions/events; it does not change this review state.

**SafetyEvaluation.outcome and RecommendationReview.state are intentionally
Python-only derived properties.** They are absent from JSON and both validation
and serialization schemas. JSON retains the constituent checks and records;
model validation recomputes the properties on round-trip. Caller-supplied derived
outcome/state fields are rejected. A future external API must explicitly decide
how to expose a read-only summary; it must not treat these properties as currently
serialized contract fields. Reference properties are likewise conveniences over
serialized identities/revisions.

Evaluations preserve exact policy/rule versions, attempted checks, scope,
limitations and uncertainty. Outcomes include hard_failure, incomplete, warning,
not_applicable and no_detected_violation. All-not-applicable checks yield
not_applicable, not apparent applicable coverage. None asserts universal clinical
validity. Unavailable checks conservatively yield incomplete, including optional
ones; intended-use interpretation belongs to a future policy engine.

Human review, acknowledgement, acceptance, rejection, modification and override
attempts remain separate immutable events. Only warnings may be designated
potentially overrideable. No event rewrites a failed finding or grants release.
A modification links a new candidate revision.

## Remaining boundaries

Governance consumes independently established authority, freshness, exact-meaning
assessment and dependency eligibility. External adapters must enforce the decisions
and establish actual delivery. No clinical content is
wired to an API. Clinical algorithms, rule engines, medication reconciliation,
terminology/FHIR mappings, evidence eligibility, provider governance, privacy,
audit storage and retention enforcement remain separate work.

Frozen models/tuples prevent normal mutation, not malicious Python or historical
storage rewrites. Use model_validate/model_validate_json at ingestion boundaries;
model_construct and model_copy(update=...) are trusted-code escape hatches.
Revalidation catches invalid nested model instances. No natural-language semantic
validation or source authentication is performed.

Field names, Literals, tuples, Decimal quantities, local graph rules and these
prototype contracts are implementation choices, not additions to the parent
standards. They change pre-commit interfaces; no external consumer or migration
compatibility is claimed. Select the initial intended use, policies, authority,
freshness ownership and reference-resolution/storage strategy before the next
clinical slice. DATA-001 Section 50.1 legacy reconciliation remains open.

## Verification and focused post-fix review

Run from the repository root:

```sh
PYTHONPATH=backend backend/venv/bin/python -m pytest -q
git diff --check
```

The four first-commit findings are addressed as follows:

| Finding | Status | Implementation and regression coverage |
|---|---|---|
| Numeric-to-Boolean coercion | Resolved | StrictBool; test_numeric_measurement_cannot_coerce_to_boolean_python/json and strict Boolean/Quantity round-trips |
| Future/unavailable calculation and contradictory administration timing | Resolved | Derived/execution availability, event-time equality, recording/cutoff checks; test_execution_and_derived_availability_at_cutoff, administration timing tests, and future planned/effective positive cases |
| Conflicting exact revisions within a bundle | Resolved | Explicit local content checks; conflicting execution/evaluation, knowledge/evidence and intermediate lineage tests, with identical reuse and new-revision positive cases |
| Zero-input missing-input failure | Resolved | Outcome-dependent inputs plus missing_parameters; test_zero_available_inputs_records_named_missing_parameters_without_references |

Additional regressions cover named conversions, unit assessment, medication
structure, target reverification, intermediate copying, independent later
confirmation, Python-only derived-property serialization, reference boundaries,
base-class behavior and all-not-applicable checks. The candidate revision test
changes only the version of rec1. Software tests are not clinical validation.


## Slice 2: release and presentation governance

`governance.py` adds ReleaseEligibilityAssessment, ReleaseDecision,
PresentationEligibilityAssessment and PresentationRecord. The pure functions in
`app/services/governance_service.py` construct auditable records; they do not
release or display content externally. Existing Slice 1 and retrieval contracts
remain unchanged.

OutputTarget binds patient/encounter (or longitudinal context), request, intended
use, destination and recipient. IdentityVerification is a separate assertion:
reverification does not change the target. GovernancePolicy is a resolved set of
requirements, not a policy interpreter. It supplies versioned rules, required
context/dependencies, warning treatment, permitted optional degraded losses and
an explicit maximum observation age. No numerical clinical thresholds are built in.

### Exact payload, policy and exception bindings

PresentationPayload is the complete delivery manifest: the rendering, every
recorded safety warning (evaluation/check/rule and reason), exact exception
proposals including rationale/conditions/actor/time/scope, and safety-evaluation
and content-validation limitations. `required_payload` assembles these declared
requirements without interpreting prose. Adapters must deliver the entire manifest.
`ReleaseDecision.released_payload` is the delivery contract; `released_content`
is only a rendering-component convenience and does not cover all required material.

ContentValidationAssertion pins both the complete review and the payload with
canonical SHA-256 digests. Release/presentation authorization pins review, payload
and exact resolved GovernancePolicy content, including its reference/version.
These hashes bind supplied evidence; they are neither signatures nor clinical
validation. Dropping dependency requirements under the same policy revision cannot
reuse unchanged authority. Changed disclosures require new payload assessment and
authorization; payload validation cannot predate its exception proposals.

Release requires matched exact meaning, in-scope validation, applicable required
check coverage and current authority/context/dependencies. No-detected-violation
and all-not-applicable results cannot assert universal clinical validity. Hard
failures remain blocking regardless of warning exceptions or HumanDecision events.

WarningExceptionProposal contains all exception terms independently of authority.
WarningException adds an authorization whose exception digest pins that exact
proposal, including identity/revision, rationale, conditions and validity. This
separation avoids a circular hash. Changing those terms cannot reuse unchanged
exception authority. The original evaluation remains unchanged. Exception and
authority windows are rechecked for presentation. This slice conservatively
requires a delivery-scoped ConditionSatisfactionAssertion for every exception's
conditions. Its trusted producer determines satisfaction; unknown, unsatisfied,
missing or differently scoped confirmations block. No condition parser is provided.
Only explicitly configured optional losses permit degraded use; required
dependency/update loss and unavailable safety checks always withhold.

### Reassessment and local integrity

`validate_governance_bundle` checks a bounded, explicit list of versioned
assertions, policies and decisions across nested records. Release and presentation
boundaries invoke it automatically. Call it also when accepting multiple separately
supplied, already validated model records. Conflicting contents under one exact
assertion identity/revision raise a validation error; identical reuse is permitted.
Reassessment requires a new revision or identity. Exception disclosures are checked
as proposal projections separately from complete authorized exception records.

DependencyState and FreshnessItem references identify observed resources, not the
assertions themselves: their observations may legitimately change. The containing
ContextFreshnessAssessment is versioned and cannot silently change. This distinction
avoids treating a new resource observation as an immutable-resource conflict.
Cross-request uniqueness and consistency against stored history remain deferred.

### Final verification and delivery evidence

Validity windows are half-open [start, end). Each required context item has its own
window; general runtime observations have a separately configured maximum age.
Presentation eligibility rechecks context, output/request status, dependencies and
presentation authority. Historical release authority is evidence for release;
current presentation requires its own authority. Original release/content windows
and warning exceptions still constrain presentation. A withheld assessment cannot
later silently mature into permission: create a new assessment.

FinalDestinationVerification is distinct from eligibility-time evidence. It binds
the presentation-record attempt, eligibility assessment, release, exact payload,
complete final RuntimeState, target and scoped condition confirmations. The final
runtime observation, verification and delivery must share the logical atomic
verify-and-deliver event time. A still-fresh eligibility-time observation cannot
stand in for a later delivery check. Equal event timestamps encode an adapter
attestation; they do not themselves prove real-world atomicity.

PresentationReceipt names that verification and attempt and retains the complete
payload actually reported delivered, target and event time. A matching receipt
cannot establish `presented` without matching final-verification evidence. Missing
verification withholds an attempted delivery; a receipt inconsistent with the
required evidence yields `rejected` and is retained. Eligible attempts with proper
verification but no receipt remain `unconfirmed`. These outcomes do not claim that
a clinician read, understood or acted on the output. A contradictory same-revision
assertion bundle is invalid input rather than a valid rejected-delivery record;
its ingestion failure must be handled by a future audit adapter.

Decision outcome and reasons are serialized and checked against supplied evidence
on validation. Eligibility summaries, availability and convenience properties are
Python-only; JSON retains the evidence needed to recompute them. Regression tests
cover schema requirements and successful/blocked JSON round-trips.

### Deliberate boundaries

These contracts trust authenticated assertion producers, a trustworthy clock and
an adapter that checks destination atomically with display and records delivery.
They cannot read live systems or prevent a dishonest adapter from inventing evidence.
Authentication/signatures, durable audit/idempotency, revocation feeds, actual
atomic display enforcement, institutional policy selection, clinical validation,
and historical evaluator migration remain integration work. Exception condition
satisfaction is a scoped external assertion, not a generic executable policy.
Policy/assertion shapes and hashing are implementation choices, not additions to
the parent standards. No UI, FHIR mapping, drug engine or workflow engine is added.

Slice 2 regression coverage is in `tests/test_governance.py`. It includes the five
adversarial reproductions: contradictory same-revision assertions, missing delivered
disclosures, reused eligibility-time evidence, changed exception terms under old
authority, and changed policy requirements under old authority. Positive cases
cover new revisions, complete delivery, scoped confirmations and round-trips.

Run the complete suite without pytest's cache:

```sh
PYTEST_ADDOPTS='-p no:cacheprovider' PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python -m pytest -q
git diff --check
```

## M6.1 recorded microbiology and antimicrobial contracts

`recorded_v2.py`, `microbiology.py` and `antimicrobials.py` are additive, frozen,
versioned contracts only. Existing M1–M5 models, canonical serialization, Kernel v1,
lineage and governance behavior remain unchanged. The twelve new fact kinds are
not admitted by persistence. M6.2 requires explicit fact-kind admission, mapping,
decoding, historical identity support and an additive migration before storage.
No assembly, inference, protected execution, API or UI integration is implemented.

Specimen, direct examination, culture, isolate identification, susceptibility,
resistance finding, molecular target, blood-culture set and bottle have independent
stable IDs and exact revision references. Names and array positions are not IDs.
Report status (including preliminary/final) is separate from change disposition
(including corrected). Correction links preserve exact supersedes references;
these pure contracts do not verify persisted revision chains or source authenticity.
Domain bindings explicitly distinguish resolved, unresolved and ambiguous targets,
with scoped stable identity and exact revision. They are not derived_from edges.

Collection, receipt, report, source availability, identification, order and delivery
times remain distinct. Missing, unknown, approximate and bounded times are explicit.
The common ClinicalTime permits recording/retrieval/processing metadata, but not
competing event/effective timestamps. Offsets and supplied precision are retained;
actual instants govern comparisons. No universal clinical time ordering is imposed.
MIC comparator, decimal scale, source units, raw interpretation and optional
breakpoint authority/version are retained. Floats are rejected, not normalized.
Resistance mechanisms and organism/agent equivalence are never inferred.

Antimicrobial identity retains source coding and an explicit mapping assertion with
bounded provenance; no name matching occurs. An order is intent. A completed
administration records delivered quantity, while held/refused/missed/not-given
records cannot contain an administered dose. Missing administration is unknown;
zero-dose pseudo-administration and continuous exposure inference are unsupported.
Therapy purpose is explicit source documentation only. These records do not prove
clinical effectiveness or validate a regimen.

All new provenance owners use BoundedProvenance: at most 32 upstream edges, 32
limitations and 16 references per confirmation basis. Source identifiers, domain
bindings, ambiguous candidates and ingredient IDs are limited to 16; role constraints
can impose smaller limits. Examination findings, disclosures and uncertainty arrays
are limited to 32. Oversize input fails without truncation. Collections become
immutable tuples; meaningful provenance declaration order is preserved.

Focused validation: `tests/test_patient_state_v2.py`, including exact-bound and
one-over-bound cases, caller alias mutation, permutations and canonical round-trips.
