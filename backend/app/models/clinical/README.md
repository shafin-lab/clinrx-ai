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
new framework, endpoint, clinical algorithm, or release engine is introduced.
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
failed evaluations. Released, presented and withheld remain reserved vocabulary
for later distinct decisions/events, not implemented transitions or writable flags.

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

Release/withholding, actual presentation, effective warning exceptions and later
eligibility changes require independently enforced authority, freshness,
exact-meaning assessment and dependency eligibility. No clinical content is
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
