# Synthetic recorded-weight contracts — Sprint 7B.1 Phases 1–2

`weight_trend.py` selects and compares retained observations and constructs a bounded
ClinicalInference. No release, rendering, execution-record storage or clinical
validation is performed.

Obtain a transaction-scoped repository and call `select_weight_observations` with
one encounter target, an explicit repository cutoff and `WeightTrendSelectionPolicy`.
The policy identifies one body-weight concept, a half-open event window [start, end),
and a separate inclusive source-availability datetime; start < end <= availability.
The datetime is not derived from the repository watermark or its capture clock.

The existing `list_latest_known` reader selects terminal visible revisions before
eligibility. No history filter, unrestricted exact read or future lookup is used.
An ineligible terminal revision never resurrects its predecessor. Distinct stable
facts are ordered by exact event instant, not ingestion order or revision labels.

V1 requires known positive quantities, assessed/normalized UCUM `kg` with raw
spelling `kg` (surrounding whitespace permitted), precise event time without time
uncertainty, verified fact/binding, conflict `none_known`, and observed/reported
origin. Provenance must declare complete lineage, no upstream links/limitations,
and measurement/clinician/external-record channel. These are restrictive synthetic
assertion requirements, not authentication or proof of real-world completeness.
Binding assessment, provenance recording and supplied recorded/retrieved/processed
times must be at or before the availability bound. Unknown optional availability
timestamps remain unknown; no timestamp is invented. Earlier measurements may be
historical. No freshness thresholds or unit conversion are implemented.

Unrelated concepts/fact categories and precisely timed out-of-window observations
are excluded. Missing/imprecise time on the configured concept cannot establish
irrelevance and blocks. Other ineligible in-window candidates also block even if
two good candidates remain. Exclusions retain exact references and reason codes.
Zero/one eligible measurement yields `insufficient_eligible_inputs`; more than two
yields `ambiguous_eligible_inputs`. Equal event instants yield
`invalid_measurement_order`. An unsuccessful result has no usable selected pair;
all its issues remain available. Storage corruption and invalid API contracts raise
their existing exceptions rather than becoming normal selection issues.

`compare_recorded_weights` revalidates the selection and returns a frozen
`RecordedWeightComparison`, or the first retained selection issue when unsuccessful.
The full issue list remains on the selection. Comparison preserves exact references,
values and event times and yields decrease/unchanged/increase. No differences,
percentages, diagnoses, causes or nutritional interpretations are generated.

Returned reads remain provisional until the repository transaction exits successfully.
These functions do not construct a ContextSnapshot, certify selection history
submitted by callers, or establish release eligibility.


## Phase 2 — inferred fact persistence and exact durable lineage

`build_weight_trend_inference` consumes the successful selection and its comparison,
plus an explicit inference identity/revision and aware execution time. It revalidates
both contracts and compares every retained comparison field against the selected
pair, including Decimal representation and event offsets. Failed selections return
an existing selection issue; inconsistent/invalid contracts raise ValueError or the
existing Pydantic ValidationError. No failure-shaped inference is created.

The method is exactly `inference_method:RecordedWeightTrend:1`. The resulting fact
is inferred and unverified, with unknown conflict/current-use status, synthetic
applicability and explicit uncertainty/validation/provenance limitations. Its inputs
and two derived_from edges preserve earlier/later declaration order. Statement text
only describes decrease/unchanged/increase, with the required synthetic limitations.
Input uncertainty is retained. No difference, percentage, prediction or advice is
produced. Execution must not precede the policy's source-availability cutoff;
inference event/recorded/processed and provenance recording times equal execution.
Binding retains the selected observation's verified target assertion; this does not
mint new identity verification or clinical verification for the inference.

The builder performs no database operations. Use existing `append_fact` and commit,
then obtain an output RepositoryCutoff including the inference. Close/reopen and
load its exact reference through `load_fact`; use existing `resolve_lineage` with
that output cutoff and explicit LineageLimits. The input cutoff cannot resolve a
root inserted later. Direct dependencies are the two consumed exact observation
revisions; inspect dependency owner/source and assertions, not just graph size.

Later corrections never replace dependencies in the stored inference. Old-cutoff
selection replays the original pair, while a new selection may use corrected inputs.
This is historical reproducibility, not continued eligibility. Reassessment,
invalidation, release-race handling, governance, rendering, execution storage and
all schema/transaction-composition changes remain deferred. The inference payload
retains exact inputs, not a durable selection policy/cutoff execution envelope;
that audit responsibility belongs to a later phase.


## Phase 3 — synthetic historical governance composition

`weight_trend_release.py` composes existing domain and governance contracts only.
Its intended use is **Synthetic evaluation of a fixed historical recorded-weight
comparison, with no patient-care use or delivery.** No execution record, database
write, API, presentation or continuing clinical eligibility is implemented.

Supply the committed original successful selection/comparison, reopened retained
inference, actual exact LineageResult, and registered patient/encounter records.
`build_weight_trend_snapshot` embeds resolved records in memory; its clinical
temporal cutoff must include inference execution/recording. It declares partial
clinical completeness with an exact narrow scope, never a complete clinical feed.
Repository prefixes, source availability and snapshot clinical time remain distinct.

`build_weight_trend_candidate` creates one deterministic descriptive ClinicalClaim
in the existing ClinicalRecommendation envelope. Its basis and copied_from
provenance identify the persisted inference; the inference remains inferred and
unverified. `render_weight_trend` generates the closed Phase 2 wording from the
comparison. No diagnosis, causality, advice, prediction or changed units are added.

`evaluate_weight_trend` executes exactly two applicable required rules:
`exact_evidence_and_input_suitability` and `bounded_descriptive_output`, version 1.
It checks retained representations, input/output prefixes, exact payloads, all
declarations/roles/ancestry/disclosures and snapshot membership; it also checks
every output-bearing claim/envelope field and independently derives the permitted
statement. Contradiction yields hard_failure; missing evidence yields unavailable.
Neither rule can establish coverage through not_applicable. Source uncertainty is
closed to the literal `synthetic uncertainty` (or absence); unsupported source
prose is not endorsed by copying it into a faithfully retained inference.

`validate_weight_trend_content` checks the actual complete review, performed
evaluation and required_payload disclosures before emitting matched/failed/
unavailable with derived review/payload digests. It accepts no caller result or
digest. Hashes establish binding, not meaning. Changed content requires new checks
and assertions, even when its hashes have been recomputed. Structural malformed
input remains a validation error; stored corruption remains a persistence error.

`assess_weight_trend_context` assesses adequacy for this fixed historical request,
not physiological freshness. It checks exact members and availability, observes
only after snapshot creation and supplies bounded per-item windows. Unknown or
missing evidence is not fresh. `material_change=False` applies only to this
immutable historical prefix; it makes no claim about changes outside that prefix.
`assess_weight_trend_dependencies` checks exact evidence and local versioned
functions; updates are not_required for this historical use. No revocation feed
or live clinical dependency availability is inferred.

`issue_synthetic_weight_release` implements SyntheticWeightReleaseIssuer/v1. Its
fixed local grant permits only synthetic-orchestrator, the synthetic-p1/e1 request,
synthetic-local destination and synthetic-reviewer recipient under the exact
resolved v1 policy. Its explicitly synthetic grant window is
[2026-09-25T14:00:01.123456Z, 2026-09-25T14:01:01.123456Z). Known disallowed subjects
are denied; unknown subjects return unknown. It checks scope, policy, disclosures,
content availability and the grant window and derives all digests. This test grant
is not production authentication, signatures or clinical authority.

`assemble_weight_trend_runtime` checks registered context and uses harness-owned
active request/output identities; current means the active output for that fixed
historical request. `weight_trend_governance_policy` requires the two rules, exact
snapshot/inference/observation context and exact evidence/local method artifacts,
with no degraded mode or warning exceptions and a synthetic 30-second observation
age. Resolved policy identities include a deterministic digest of their exact
requirements, so different context manifests cannot conflict under one immutable
policy reference; the profile remains version 1. This interval is not a clinical freshness threshold.

`release_weight_trend` composes these producers with unchanged assess_release and
decide_release. released means the exact payload satisfied this synthetic policy
at decision time; withheld retains existing governance reasons. Neither means
approved, presented, delivered, received, accepted or acted upon. The existing
ReleaseDecision may round-trip in memory; no durable decision history is claimed.

The local harness remains responsible for supplying real committed reads and
protecting its controlled request state. These functions validate consistency,
not source authenticity or original selection membership against fabricated reads.
Later corrections do not rewrite the fixed historical proof. Phase 4 owns the
final relevant-context recheck and decision/execution-record transaction.

Focused verification: tests/test_weight_trend_release.py; existing weight,
governance/safety and persistence/history/lineage regressions remain applicable.


## Phase 4 Increment 1 — execution contracts and pure final recheck

`weight_trend_execution.py` defines immutable in-memory contracts only. It adds no
storage, schema, SQL, transaction API or release orchestration. The record describes
a Phase 4 attempt over an already successful original selection/comparison and
exact Phase 2 inference identity. Failures before that evidence exists are outside
this narrow envelope. No new generic execution or audit framework is introduced.

Allocate a caller-generated UUID before the attempt. `WeightTrendExecutionRecord`
retains the complete OutputTarget (context, immutable request ID, intended use,
destination and recipient), actor, original manifest/comparison, inference reference,
optional available lineage/recheck evidence, implementation version and start/finalization
times. Neither time is a database commit timestamp. Repository identity is derived
from the original cutoff. The complete existing ReleaseDecision retains producer,
profile, safety, fidelity, policy and authorization identities without new wrappers.
There is no separate software build identity convention to add here.

Exactly one of `decision` and `issue` is required. Decision records require lineage
and a final recheck and derive `completed_released` or `completed_withheld`.
Operational records derive `failed_operationally` and never fabricate a decision;
lineage/recheck may be absent when that step failed. The issue contains only bounded
stage/code literals, with no free-text exception, SQL, stack trace or patient values.
Future adapters must sanitize exceptions; arbitrary validation exception strings
are not this persistence contract. All records, including withholdings and failures,
are frozen; there is no mutable status or revision chain.

Later persistence must interpret same UUID + identical canonical payload as
idempotent recovery, same UUID + different canonical payload as content conflict,
and genuine re-evaluation as a new UUID. Those retry/recovery behaviors are not
implemented or established by constructing an envelope.

`WeightTrendSelectionManifest` retains target, full small selection policy (pinning
its parameters as well as v1 identity), repository cutoff, ordered exact references,
aligned canonical payload digests, and existing exclusions/issues. Success is
derived from absence of issues. Failed selection retains no usable pair. Blocking
exclusions must agree with input issues. No observation bodies are duplicated in
the manifest; the original comparison retains exact values and event representations.
Exclusion/issue declaration order is preserved rather than compared for material change.

`weight_trend_lineage_witness` projects a supplied actual LineageResult into the narrow
one-inference/two-observation declared graph. It retains exact ordered derived_from
edges, ingestion-ordered body-free nodes with canonical payload digests, metadata,
evidence roles, sorted self-inclusive ancestry, provenance limitations, coverage and
sorted unresolved disclosures. Extra/mismatched graph structure is rejected.
Revision supersedes links are not evidence. Partial lineage can explain a withheld
unavailable-evidence decision; missing snapshot bodies are not fabricated. Present
bodies must match retained digests, order and comparison; released decisions require
complete evidence. An envelope checks consistency, not source authenticity.

`assess_weight_trend_final_recheck` implements WeightTrendFinalRecheckPolicy/v1.
Supply the original and final Phase 1 results plus a scoped inference-terminal check.
The same exact selection-policy parameters and patient/encounter must be used, in
the same repository with a nondecreasing watermark. Only the repository cutoff
changes; source availability and the half-open event window remain fixed. The function
does not query, reselect, generate safety/freshness assertions or decide release.
Terminal inference lookup and protected final selection belong to later orchestration.

Failure of final selection, a changed ordered exact pair (even numerically equal),
or a superseded consumed inference is material change. Terminal ineligibility,
third-input ambiguity, conflicts, timing/source-availability failures and selected
facts leaving the window/concept are handled by the unchanged Phase 1 selector.
An unavailable terminal lookup is `unavailable` unless another material change is
already established. Reasons and outcome are deterministic derived properties.
Inference insertion, unrelated insertions, harmless out-of-window observations and
benign exclusion growth alone do not make an unchanged pair material.

Contradictory canonical bodies under an overlapping selected exact reference raise
the existing payload-free StorageIntegrityError, even if another reference changed.
Malformed supplied contracts raise validation errors. Failed Phase 1 results omit
excluded bodies: their integrity must already have been established by the trusted
reader. Digests and caller-supplied terminal status cannot prove a repository read,
completeness, absence of corruption or a database commit. A changed/unavailable final
check cannot accompany a released decision; a corresponding withheld decision must
retain inadequate freshness and, for material change, the material-change flag.
This is a consistency check, not the later final-context assertion producer.

Use existing `canonical_payload` and validated JSON reloading. Payload version 1 is
explicit and unsupported versions fail. Keys/defaults use existing canonical rules;
array order, Decimal lexical representation and timezone offsets remain material.
Set-like ancestry and unresolved disclosures are explicitly ordered. Derived fields
recompute on reload. Unsupported lossy timestamp serialization fails through existing
mapping conventions; no alternative serializer is introduced.

Increment 2+ still owns the table/migration/entity/adapter, storage idempotency and
conflicts, protected shared transaction, actual final re-selection and terminal lookup,
final governance composition, commit/recovery behavior and multi-connection race tests.
API/frontend, reverse lineage, reassessment and withdrawal remain deferred. None of
these contracts establishes clinical validation, production authorization or delivery.

Focused verification: `tests/test_weight_trend_execution.py` uses synthetic pure
fixtures, including real existing Phase 3 decision composition, without database fixtures.


## Phase 4 Increment 2 — durable recovery of the execution envelope

The separate `app.persistence.executions` adapter now supports immutable scoped
append/load of this contract, including its complete recorded decision or operational
failure. See the persistence README for the one-table migration, canonical digest,
idempotent retry, privacy and recovery semantics. These calls own independent
transactions; they must not be nested inside a fact repository transaction.

A recovered record is historical evidence. Standalone storage does not make final
context checks and release decisions atomic. The Increment 4 workflow below adds
that protected composition. Storage alone does not establish continuing release
eligibility, presentation or delivery.


## Phase 4 Increment 3 — shared persistence primitive

`app.persistence.shared_transaction.execution_transaction(engine)` provides one
private session and BEGIN IMMEDIATE for `tx.repository` and `tx.executions`.
The execution adapter offers append(record, target=...) and load(execution_id,
target=...). An exceptional operation through either handle poisons both, even
when caught; outer exit rolls back. Successful outer exit alone establishes commit.
All handles close after exit. Use these handles rather than nesting standalone
persistence calls, which continue to own independent Engine-only transactions.
See the persistence README for lifecycle, privacy, retry and completion semantics.

This increment does not compose final selection, terminal lookup, material-change
assessment, final governance or execution-record insertion into a clinical workflow.
Increment 4 below adds the protected workflow and correction-race tests; automatic
commit-outcome reconciliation remains Increment 5. Increment 3 itself changes no
execution-domain contracts or clinical release behavior.


## Phase 4 Increment 4 — protected synthetic weight review

```python
from app.execution.weight_trend_workflow import (
    WeightTrendReviewRequest, execute_weight_trend_review,
)

stored = execute_weight_trend_review(engine, request, clock=trusted_clock)
# Returned StoredWeightTrendExecution means the owning context exited successfully.
```

The frozen request carries execution_id (caller UUID), complete OutputTarget,
actor, original successful selection manifest, comparison, exact inference reference,
compact lineage witness and requested_at. It accepts no final selection, snapshot,
candidate, authorization, runtime state or decision. These historical assertions
are independently checked against storage; they do not authenticate sources.

Inside one execution_transaction, a scoped normal-absence find checks retry identity
before any clinical reads or runtime clock sampling. An identical canonical request
projection recovers the original execution without selection/governance recomputation,
even after later corrections. The projection includes all request fields, mapping
requested_at to started_at; generated final evidence and ingestion metadata are
excluded. The retained decision assessment must name SyntheticWeightProtectedExecution/v1.
This marker distinguishes the application workflow convention, not cryptographic
proof against privileged writers. Other request content or incompatible legacy
records conflict. No request digest, registry, mutable status or schema field is added.

For new work, a cutoff captured under BEGIN IMMEDIATE bounds the protected final
prefix. The workflow writes no facts. It replays the original selection and compares
its complete canonical manifest, including ordered exclusions/issues, then reconstructs
and compares the exact comparison (including Decimal scale and timestamp offsets).
It resolves historical lineage at the request's output cutoff, checks the complete
compact witness, and rebuilds the retained inference against the Phase 2 grammar.
Contradictions, invalid retained inference timing, unsupported weight lineage and
missing required evidence abort; they are not fabricated clinical withholding.

Final selection uses exactly the original policy with only the repository cutoff
changed. Existing terminal-before-eligibility, kg-only, event ordering, source
availability and cardinality semantics remain unchanged. The existing latest-known
inference-family reader supplies the terminal check, without filters or automatic
replacement. WeightTrendFinalRecheckPolicy/v1 is unchanged. A changed exact reference
(including a same-value correction), ineligible terminal, third eligible observation
or superseded inference causes material change. Unrelated facts and harmless exclusion
growth do not automatically invalidate the comparison. Same-reference contradictions
are integrity failures. An inexplicably absent previously verified inference family
is an integrity failure in this append-only workflow.

Fresh snapshot/candidate/rendering/safety/fidelity/dependencies/authorization/runtime
and release assessment/decision are built under that transaction. The separately
identified SyntheticWeightFinalContext/v1 producer retains historical suitability
checks and adds final-recheck evidence. On material change it sets inadequate context,
material_change=True and bounded stale items. Governance still reviews the ORIGINAL
historical evidence; correctly passing historical safety/fidelity checks are not
fabricated failures. Existing assess_release/decide_release derive withholding.
Phase 3's historical producer and governance policy semantics are unchanged.

requested_at is immutable request metadata, retained as started_at. Trusted runtime
clock samples occur after transaction acquisition, at governance observation, at
final decision/authorization and at finalization. Runtime values are aware UTC and
must not move backward. Repository cutoff capture time and execution ingestion time
are not commit timestamps. Evidence validity is evaluated at decision time. The
existing fixed September 25, 2026 synthetic grant is unchanged: happy-path tests use
an explicit controlled clock within it; current/out-of-window clocks normally withhold.
No production identity or clinical authority is implied by the supplied actor.

The existing WeightTrendExecutionRecord retains actual reconstructed historical
manifest/comparison/lineage, protected final recheck and complete release OR withholding
decision. tx.executions.append runs inside the same transaction. Only after successful
context exit is its immutable result returned, without a second transaction. Execution
insertion does not change clinical fact watermarks, history or lineage.

Adapter failures poison the shared transaction. Pure builder/integrity exceptions
escape it before public error translation; no lifecycle reset or public poison method
is needed. Public errors use bounded existing categories and suppress sensitive chains.
KeyboardInterrupt/SystemExit propagate. No automatic operational-failure execution
row is written. Valid withholding commits as a completed historical execution.

Completion uncertainty returns no success and does not claim definite rollback.
Automatic reconciliation and delivery remain Increment 5+. An explicit same-ID retry
first reads: if present, it recovers the exact retained result; if absent, it can run
a new protected evaluation for that still-unretained attempt. New evaluation of an
already retained execution requires a new UUID and coherent historical evidence.

Focused tests: tests/test_weight_trend_workflow.py. Independent zero-timeout writers
cannot insert corrections or third measurements between final recheck and execution
append; changes committed before acquisition are seen and changes after commit do not
rewrite the retained decision. Lock-wait tests use events and verify clocks/authorization
are sampled after acquisition. Fault injection covers pre-commit rollback and actual
commit followed by an exception, without implementing reconciliation. No delivery,
reassessment, reverse graph, migration, payload-version change or generic workflow.


## Phase 4 Increment 5 — explicit commit-outcome reconciliation

`reconcile_weight_trend_execution(engine, request)` answers whether this repository
contains a valid retained protected execution matching the immutable request. It
accepts an Engine and the existing `WeightTrendReviewRequest`, with no clock,
automatic execution, retry policy or delivery behavior.

The frozen `WeightTrendReconciliationResult` has exactly two outcomes:
- `committed_match`, with the exact `StoredWeightTrendExecution`, including original
  ingestion metadata. Both released and withheld protected decisions qualify.
- `absent`, with execution None: no retained execution under this ID and expected
  scope was visible in the supplied repository during this lookup. This does not
  prove that a transaction never committed, authorize delivery, or describe another
  repository or a later lookup.

The standalone loader validates version, digest, canonical envelope, repository
identity and ownership before the shared protected request-match helper runs.
Matching uses execution_id, complete target, actor, original manifest, comparison,
inference, lineage and requested_at (stored started_at), preserving canonical
Decimal/time representations and order. The decision must bear exactly
SyntheticWeightProtectedExecution/v1. The marker is a convention, not authentication.
Final cutoff/recheck/decision, finalization time and ingestion metadata are validated
as retained data but are not request identity. Standalone operational-failure or
legacy envelopes do not establish protected completion and conflict.

Missing and foreign-scope rows are indistinguishable absence; foreign payloads are
never decoded. Valid in-scope incompatible requests/markers raise RecordConflict.
Visible corruption raises StorageIntegrityError before matching. Invalid requests
raise PersistenceInputError, unsupported schema raises SchemaMismatch, and read or
unexpected failures raise sanitized TransactionAborted. Reconciliation failure
leaves prior uncertainty unresolved; it is never represented as absence or success.
Process-control exceptions propagate. Standard formatted errors suppress internal
exception chains; Python exception context remains introspectable.

The API performs no application DML or current clinical reads. Existing pure
retained-envelope validation remains active. Corrections, third observations,
inference supersession and expired authorization do not refresh a stored decision.
Recovery establishes historical completion, not current eligibility, authorization,
delivery, or which invocation committed the row. Required repository/ownership
integrity still applies. Reopen/process recovery uses only durable state.

After explicit absence, a caller may explicitly retry execute_weight_trend_review
with the same ID/request. Its protected lookup remains authoritative: an intervening
matching row is returned, incompatible content conflicts, and continued absence
permits a new evaluation. Current evidence may then produce a different decision.
No lost provisional decision is reconstructed from memory.

Execution completion uncertainty now raises TransactionCompletionUnknown, a subtype
of TransactionAborted, retaining the bounded message "transaction completion could
not be confirmed". Branch on type, not message. Neither this subtype nor ordinary
abort messages establish that a commit or rollback definitely occurred.

Reconciliation uses the existing standalone loader, including BEGIN IMMEDIATE and
its potential writer contention. RecordNotFound is translated only after that call
has unwound; no shared poisoned handle is reused. No new read policy, schema,
payload version, automatic execute/reconcile wrapper, background worker, mutable
status, delivery deduplication or generic recovery framework is introduced.


## Slice #2 Phase A — synthetic serum-creatinine selection and comparison

`creatinine_trend.py` implements only `select_creatinine_observations` and the pure
`compare_recorded_creatinine`, with separate frozen creatinine contracts. Supply
an encounter target, repository cutoff and `CreatinineTrendSelectionPolicy` v1.
The concept is fixed to `synthetic-serum-creatinine`; unit is exact raw/UCUM `mg/dL`
with assessed/normalized status and a finite, strictly positive Decimal. No unit
conversion, trimming, rounding or clinical thresholds are applied.

Terminal visible revisions are selected by unchanged unfiltered history before
eligibility. The sample/event window is half-open and the separate availability
bound inclusive. Event, recorded, retrieved and processed times are required in
that instant order; provenance recording equals result recording by instant.
All availability and binding-assessment times must satisfy the bound. Comparison
orders by sample instant, preserves offsets and Decimal scale, and rejects ties.

The synthetic source namespace is `clinrx.synthetic.serum-creatinine`, version `1`,
with measurement/external_record channel. Its identifier names one sample.
Verified fact/binding, conflict none_known, complete provenance without upstream
or limitations, and only the permitted synthetic uncertainty disclosure are required.
Duplicate sample keys among relevant terminals block independently of eligibility.
Two distinct stable IDs and two distinct sample keys are both required; this is
not real laboratory specimen authentication or deduplication.

Relevant exclusions block even with two otherwise eligible inputs. Exactly two
eligible observations are required; more than two is ambiguous, never latest-two.
Issues/exclusions follow terminal ingestion order; duplicate issues follow that
record's eligibility issue, then cardinality issues. Any issue leaves no selected
pair. Comparison revalidates selection and returns its first issue on failure;
malformed contracts/storage raise rather than becoming ordinary selection issues.
Returned contracts establish consistency, not proof that caller-supplied evidence
came from a repository. Selection and comparison perform no writes.

The comparison contains only exact references, values, unit, sample times and
direction. Inference construction, lineage witness, governance, final recheck,
execution persistence, reconciliation and delivery remain deferred. Kernel and
weight behavior are unchanged. See CLINRX-CAP-001 for the full source contract;
focused tests are in `tests/test_creatinine_trend.py`.


## Slice #2 Phase B — inferred fact and exact durable lineage

`build_creatinine_trend_inference(selection=..., comparison=..., inference_id=...,
executed_at=..., revision='1')` is a pure builder returning the unchanged
ClinicalInference. Failed selection raises ValueError; malformed selection or
comparison raises validation errors. No failure-shaped inference is emitted.
The builder revalidates Phase A eligibility, scope, sample distinctness and order,
then checks every comparison field against the exact selected pair, including
Decimal scale and sample-time offsets. It performs no storage access or clock lookup.

Method identity is exactly `inference_method:RecordedCreatinineTrend:1`. The three
statement patterns, applicability, uncertainty and validation/provenance limitations
are exactly those committed in CLINRX-CAP-001 section 8. Increase/decrease use
`increased/decreased from {A} mg/dL to {B} mg/dL between the selected samples`;
unchanged retains both source representations as `({A} mg/dL then {B} mg/dL)`.
No rounding, delta, percentage, diagnostic/causal interpretation, assay harmonization,
reference-range interpretation, conversion or recommendation is performed.

The inference is inferred/unverified, with unknown conflict/temporal status and
binding retained from the earlier observation. Inputs and the two derived_from
edges are exactly earlier then later. System source is clinrx.synthetic /
RecordedCreatinineTrend / 1; actor is RecordedCreatinineTrend/v1. The explicit aware
executed_at must be at or after available_at by instant and supplies event, recorded,
processed and provenance recording times. Target/horizon remain None and validation
references empty. Required uncertainty is followed by deduplicated permitted input
uncertainty. Synthetic sample identity and source authenticity remain assumptions.

Persist with unchanged append_fact and capture an output cutoff after successful
transaction exit. The input cutoff cannot see the later inference. Generic
resolve_lineage with an explicit scope/cutoff/budget supplies the actual retained
graph. Phase B tests verify the root, ordered declarations/dependencies, exact nodes,
evidence roles, ancestry, ingestion metadata and disclosures. No capability witness
or new lineage wrapper is introduced. Complete declared graph coverage is not
clinical/source completeness or biological independence.

Missing, future, wrong-scope or unsupported ancestors remain explicit unresolved
entries with partial coverage. Missing roots, corrupt visible history, prohibited
cycles and exhausted budgets retain their existing exceptions. No category is
converted into an ordinary inference result. Generic storage/lineage does not
certify this capability's exact two-input contract for arbitrary caller-created
ClinicalInference objects; extra generic declarations remain visible.

Later observation corrections never substitute inside a retained inference, including
same-value corrections. New selections may use corrected evidence. Inference
corrections use existing reasoned append_revision: each exact inference revision
resolves its own inputs, while supersedes links remain outside evidence lineage.
Exact retries retain original metadata; changed content under the same ref conflicts.
The inference does not duplicate the selection policy/cutoff or sample times in its
payload: exact inputs resolve retained observations; later execution evidence owns
any durable selection manifest. Returned contracts establish consistency, not source
authentication or proof that supplied selections came from a repository.

Focused tests: `tests/test_creatinine_trend_inference.py`. Governance, snapshots,
safety/fidelity, authorization, final recheck, execution storage, transaction changes,
reconciliation and delivery remain deferred. Kernel v1 and weight behavior are unchanged.


## Slice #2 Phase C — bounded synthetic governance composition

`creatinine_trend_release.py` composes supplied Phase A selection/comparison,
retained Phase B inference and generic LineageResult into the unchanged governance
contracts. Callers obtain committed evidence first; Phase C performs no database
access, final selection, protected recheck, persistence or delivery.

The partial ContextSnapshot contains the two retained observations and inference,
registered patient/encounter, sources and explicit limitations. Its scope binds
selection, comparison and output-cutoff digests using existing content_digest.
These pins establish consistency, not authentication or a durable execution
manifest. Missing retained nodes stay missing. ClinicalRecommendation is only the
existing output envelope: its single deterministic claim copies the descriptive
inference, with applicability, uncertainty and limitations, without treatment advice.
Rendering preserves CAP-001's exact three statements and Decimal representations.

Exactly two required, non-overrideable safety rules check exact evidence/input
suitability and bounded descriptive output. Explicit mismatches hard-fail; unavailable
required evidence remains unavailable; passing means no detected violation of these
bounded rules. Fidelity independently derives wording from selected Decimal values,
checks the exact Phase B contract, performed evaluations and complete payload. Generic
assess_release and decide_release remain unchanged, with no degraded exceptions.

Historical context assertions establish suitability only for the supplied cutoffs,
within an explicit validity window. They do not detect later corrections or establish
current clinical eligibility. Dependencies retain exact refs and local versioned
methods/rules; declared graph completeness is not biological independence.

SyntheticCreatinineReleaseIssuer/v1 uses SyntheticCreatinineReleaseGrant:1, distinct
from weight. The fixed local v1 grant permits synthetic-creatinine-orchestrator,
synthetic-p1/synthetic-e1, synthetic-creatinine-request, intended use
SyntheticHistoricalCreatinineComparison:1, destination synthetic-creatinine-local,
and recipient synthetic-creatinine-reviewer. Its UTC window is half-open:
2026-10-04 12:00:00 through 12:05:00. Controlled synthetic runs must explicitly supply
a time within that window; other actors/targets/times are denied. This is fixture
policy, not production authentication or clinical authorization. Runtime composition
rejects another issuer and checks registered scope, active request and output.
Resolved governance policies use SyntheticCreatinineHistoricalRelease/<digest>:1
so differing exact context/dependency requirements do not share an immutable identity.

Released means only that this bounded synthetic output passed policy for supplied
historical evidence at assessment time. It does not mean current status, clinical
validation, patient-care approval, delivery or action. Withheld records policy or
required-evidence failure in memory. Malformed contracts and actual storage/lineage
exceptions propagate; process-control exceptions are not converted into decisions.
Trusted producers remain a project convention, not a cryptographic trust boundary.

Focused tests: tests/test_creatinine_trend_release.py. Phase D execution records,
durable decisions, protected transaction/final recheck and reconciliation remain
deferred. Generic models/services, frozen Kernel v1 and the weight slice are unchanged.


## Slice #2 Phase D1 — pure execution contracts and final recheck

`creatinine_trend_execution.py` adds immutable capability-specific contracts only.
It performs no SQL, clock lookup, authorization, release decision, transaction,
persistence, workflow execution or reconciliation. It imports no weight types.
A valid record or StoredCreatinineTrendExecution does not establish actual storage,
protected execution or commit; future trusted readers/workflow must provide that evidence.

CreatinineTrendSelectionManifest v1 retains target patient/encounter, complete
selection policy and input cutoff, exact selected refs and canonical SHA256 payload
digests, exact sample identities, Decimal values and sample times, and ordered
exclusions/issues. The redundant value/time representations permit exact comparison
validation without decoding fact bodies. Selected samples retain namespace/identifier
in selection order; existing Source parsing has already occurred, and the manifest
performs no extra normalization or authentication. A successful manifest requires two
distinct stable observations and sample keys. Failed manifests retain no invented
selected evidence. Duplicate-sample issues can exist without eligibility exclusions;
when both occur, the eligibility issue precedes that terminal's duplicate disclosure.
Full historical replay, not this compact manifest, proves actual cardinality and reads.

CreatinineTrendLineageWitness v1 pins the supplied exact two-input graph: root/scope,
output cutoff, ordered derived_from declarations, ingestion-ordered nodes with exact
refs/digests/metadata, evidence roles, ancestry and provenance disclosures, coverage
and unresolved entries. Ancestry sets receive deterministic reference ordering;
declaration, node and issue arrays remain ordered. Missing observation ancestors
remain partial/unresolved. Extra or contradictory graph structure is rejected rather
than pruned. Generic resolver semantics and exceptions are unchanged. This witness
neither establishes complete clinical provenance nor biological independence.

CreatinineTrendInferenceTerminalCheck v1 carries consumed ref/digest, historical
output cutoff, final cutoff, and terminal ref/digest. Same-ref different digest is a
contract error. None terminal requires explicit check_not_performed or reader_unavailable;
it never means the verified family disappeared. D4 must treat an actual absent family
as integrity failure. No terminal lookup occurs here.

`assess_creatinine_trend_final_recheck(original=..., final=..., inference_terminal=...)`
accepts validated selections or manifests. CreatinineTrendFinalRecheckPolicy:1 and
CreatinineTrendFinalRecheck:1 preserve the full original manifest, final manifest and
terminal assertion. Original must succeed; scope/policy/repository must match and
input < historical output <= final watermark. Cutoff capture times do not determine
visibility. Same exact ref with a different payload digest raises StorageIntegrityError;
other impossible supplied contracts/representations fail validation. Outcome/reasons
are derived, never independently writable status fields.

Exact refs/digests/sample identities/representations plus current inference are
unchanged. Replacement revision (even same value), unsuccessful final selection,
third/duplicate sample, terminal ineligibility or superseded inference is material.
Harmless exclusion growth, unrelated prefix growth and watermark-neutral execution
activity are not automatically material. Unavailable check evidence cannot establish
release. If selection is already materially changed, that outcome remains material
even when the inference check is unavailable; both reasons are retained. A failed
manifest lacks observation bodies: D4 historical replay must detect contradictions
that cannot be established from the compact supplied evidence alone.

CreatinineTrendReviewRequest contains exactly execution_id, complete target, actor,
original manifest, comparison, inference ref, lineage and requested_at. The pure
`creatinine_trend_request_projection(request_or_record)` returns existing canonical
JSON for precisely those fields, preserving scale, offsets, ordering and cutoff
metadata. It does not match requests or query storage. Generated final recheck,
governance, started_at/finalized_at and ingestion metadata are excluded from identity.

CreatinineTrendExecutionRecord v1 requires complete original lineage, final recheck
and typed ReleaseDecision. The nested decision retains snapshot/candidate/rendering,
safety/fidelity/context/dependencies/authorization/runtime and assessment; these are
not duplicated in arbitrary dictionaries. Cross-validation binds snapshot bodies,
sample identities, comparison, inference, witness digests/provenance, recheck and
request. Valid inference supersedes/correction_reason metadata remains canonical
content, not an evidence edge. Record validation cannot verify revision-chain storage.
The exact protected assessor marker is SyntheticCreatinineProtectedExecution/v1 and
final-context marker SyntheticCreatinineFinalContext/v1. Markers are compatibility
conventions, not authenticated proof that the future workflow ran.

requested_at is immutable caller metadata. started_at and finalized_at are distinct
generated execution times, ordered by actual instant around assessment/decision.
Fresh governance artifact times must fall within started_at and decision time;
historical clinical times are not rewritten. Changed/unavailable final recheck
requires withheld/inadequate context; material_change must agree with the recheck.
A valid withholding decision is retained, never replaced by an operational failure row.
No operational-failure envelope is introduced. Partial witnesses may be represented
and requested, but cannot masquerade as completed protected historical evidence.

StoredCreatinineTrendExecution contains the revalidated record and supplied original
UTC ingested_at only. It preserves that metadata and invents neither a sequence nor a
commit time. All contracts follow existing frozen/revalidation conventions and
canonical_payload serialization; unsupported lossy timestamps fail explicitly.

Focused tests: tests/test_creatinine_trend_execution.py, using pure synthetic evidence
and independent expected fields with no database fixtures. D2 table/adapter/migration,
D3 shared transaction extension, D4 protected replay/final context/workflow, and D5
reconciliation remain deferred. Existing kernel, governance and weight behavior are unchanged.


## Creatinine Phase D4: protected durable workflow

`execute_creatinine_trend_review(engine, request, *, clock=...)` in
`creatinine_trend_workflow.py` composes the existing creatinine A–D3 contracts.
This is capability-specific workflow composition, not a generic execution framework.
It accepts an Engine and a validated CreatinineTrendReviewRequest. Caller-owned
Sessions/Connections are rejected by the existing shared transaction boundary.

Within one protected transaction, scoped execution lookup precedes clock sampling
and clinical work. An exact canonical request and workflow marker match returns the
retained record, finalized_at and ingested_at after successful context exit. A
same-ID/different-request retry conflicts; retries neither reauthorize nor read
current facts. This remains true after later corrections or synthetic grant expiry.

A new execution samples a trusted aware clock after acquiring the writer lock,
captures a final fact cutoff, and replays original selection/comparison at the input
cutoff and exact inference/lineage at the output cutoff. Canonical replay preserves
Decimal scale, timestamp offsets, sample identities, ordered evidence and cutoff
metadata. The Phase B inference rebuild preserves valid supersedes/correction_reason
content without treating revision ancestry as evidence dependencies. Required
historical contradictions, incomplete lineage and impossible terminal inference
evidence abort without a completed execution row.

The same-policy final selection and inference-family terminal read feed the existing
pure final recheck. Same-value corrections, supersession or changed eligible samples
are material and produce durable withholding; unrelated/excluded growth is not
inherently material. No replacement inference is persisted. Fresh Phase C artifacts
and unchanged generic governance decide release or withholding. The final-context
assessor SyntheticCreatinineFinalContext/v1 binds the full retained final recheck
and lineage witness through canonical digests; the execution record retains the
underlying evidence. The workflow marker is SyntheticCreatinineProtectedExecution/v1.
These markers are compatibility conventions, not authentication proofs.

Runtime samples are aware, normalized to UTC and nondecreasing across start,
observation, decision and finalization. The fixed synthetic grant window remains
2026-10-04 12:00–12:05 UTC; the default current clock outside that window yields
withholding. Tests inject historical trusted runtime times inside that window;
this facility is not production authorization.

The D2 append participates in the existing D3 transaction and only the transaction
owner commits. Return occurs after successful context exit. Operational failures
roll back; uncertain completion preserves TransactionCompletionUnknown and does
not return a provisional result or trigger automatic recovery. Public errors use
bounded messages with suppressed exception chaining. Process-control exceptions
retain existing cleanup behavior.

Focused tests: tests/test_creatinine_trend_workflow.py. Shared transaction lifecycle,
persistence/schema, generic lineage/governance and weight behavior remain unchanged.
D5 explicit reconciliation and completion-uncertainty APIs remain deferred, along
with delivery, production authorization/PHI and any generic workflow abstraction.

## Creatinine Phase D5: explicit reconciliation

`reconcile_creatinine_trend_execution(engine, request)` explicitly checks whether an
exact protected execution is durably retained. Its frozen
`CreatinineTrendReconciliationResult` has only `status` and `stored`:
`committed_match` requires the retained StoredCreatinineTrendExecution; `absent`
requires None. Released and withheld decisions are equally recoverable completions.

Request validation and canonical projection precede the existing scoped standalone
`find_creatinine_trend_execution` lookup. D4 retries and D5 reconciliation share
`_require_creatinine_request_match`, including the exact protected workflow marker.
All eight D1 immutable request fields participate; generated final evidence,
governance, decision and ingestion/finalization metadata do not enter request identity.
Those retained fields still undergo unchanged D1/D2 integrity validation and are
returned without replacement. An invalid stored workflow marker fails D1 decoding
as StorageIntegrityError; a valid different in-scope request raises RecordConflict.

Reconciliation invokes no clock, clinical repository query, workflow replay,
selection, lineage resolution, final recheck producer or governance producer. It
does not reauthorize or assess current clinical eligibility. Existing D1 validation
still checks the retained comparison and reconstructs the expected inference purely
from the stored snapshot for canonical integrity; D2 still validates repository and
patient/encounter ownership. These checks do not read current fact revisions, replace
retained evidence or generate a new decision. Their semantics are not bypassed.

The standalone lookup retains the existing SQLite BEGIN IMMEDIATE policy. It performs
no application DML but can encounter writer-lock contention. Scope filtering precedes
payload decoding: missing and foreign-scope rows both yield absent; foreign corrupt
payloads remain undecoded. Visible corruption, schema/input failures and operational
failures remain bounded exceptions, never absence. Process-control exceptions retain
cleanup behavior. No shared transaction lifecycle or persistence policy changed.

After TransactionCompletionUnknown, the caller may explicitly reconcile. A committed
match preserves the original record, decision, finalized_at and ingested_at, even
after later corrections, supersession or authority expiry. Absence describes only
that completed lookup, not proof of historical rollback or permission to reuse an ID
without checking. The caller may subsequently invoke D4 explicitly; D4 checks again.
A failed reconciliation leaves the earlier completion uncertainty unresolved.
There is no automatic execute/reconcile wrapper, retry, polling or recovery loop.

Focused coverage: tests/test_creatinine_trend_reconciliation.py. This is
capability-specific explicit recovery/reconciliation, not new kernel infrastructure.
D5 completes the planned D1–D5 composition subject to the recorded validation results;
production authorization, PHI handling and delivery remain outside this synthetic slice.

## Multidomain Patient State v1 — M1 contracts only

`patient_state.py` defines PatientStateScope, RetainedStateItem, ten typed recorded
payloads, and PatientStateSnapshot. PatientStateSnapshot is clinical evidence supplied
for future reasoning; it does not reuse governance ContextSnapshot and establishes
neither release eligibility nor an inference dependency graph. No assembly, repository
query, clinical inference, governance execution or storage API is implemented.

PatientStateScope v1 carries patient/encounter IDs, aware review_start/review_end and
the existing RepositoryCutoff (repository UUID plus fact watermark). The review
interval is explicitly closed [start, end], with equal bounds permitted. Comparisons
use actual instants while canonical serialization preserves wall time and UTC offset.
Cutoff captured_at is metadata, not clinical time or a source-availability threshold.

RetainedStateItem carries one exact Reference (including revision), Binding, observed
or reported origin, ClinicalTime, Provenance, optional IngestionMetadata, verification,
conflict/temporal status, ordered disclosures and a discriminated typed payload.
Domain is derived from the payload; it cannot disagree with a separate domain field.
Reference category must suit the payload domain. Each exact source reference appears
at most once in a snapshot, including across domains. Different revisions may coexist:
M1 does not select terminal revisions or claim the snapshot is current.

The supplied payload_digest is SHA-256 of the typed domain payload's existing
canonical_payload serialization and is validated. It is NOT the digest of a persisted
PatientFact/FactRow. The Python-only canonical_digest property covers the complete
item or snapshot, including its source, exact ref, times and metadata. Digests detect
inconsistency, not source authenticity. There is no second serializer. Decimal scale,
unit spelling, offsets and meaningful source-array/disclosure ordering are preserved
under existing domain conventions. Unsupported lossy timestamps are rejected.

Payloads reuse ClinicalValue, Quantity/Unit, MedicationIdentity, Dose/Frequency and
Source. LaboratoryState retains concept, value, specimen identity/type and recorded
status. MedicationState retains identity, optional dose/route/frequency/schedule and
source status; AntimicrobialState is separately discriminated with optional explicitly
recorded indication. HemodynamicSupportState retains support/agent identity, status,
rate/dose and typed parameters. RespiratorySupportState and RenalSupportState retain
source mode/modality, status and parameters. FluidOutputState retains category,
quantity and site; negative recorded balances are not reinterpreted. MicrobiologyState
retains specimen identity/type, collection time, reported organisms, result/status and
typed susceptibility observations. ProcedureState and HistoryEventState retain source
concept, status and optional recorded context/site. Open source text avoids named-drug,
transplant or ICU policy enums. Recorded labels, including diagnoses, remain source
assertions rather than diagnoses produced by M1.

Each item declares temporal_basis:
- event: an explicit clinical event must lie in the closed review interval;
- effective_interval: a supplied effective start is required and its recorded interval
  must overlap the review interval; a missing end stays unknown, not proof of activity;
- contextual_history: only HistoryEventState may predate the review start, and its
  event (or effective start when event is absent) cannot follow review_end.

ClinicalTime retains event, recorded, retrieved, processed and effective timestamps;
Provenance retains recorded_at and MicrobiologyState separately retains collected_at.
No availability time is synthesized, no source eligibility is inferred, and ingestion
never substitutes for clinical time. Existing ClinicalTime validation remains unchanged;
M1 additionally rejects effective intervals reversed by actual instant. Actual source
mapping and domain-specific temporal/availability eligibility belong to M2 or later policy.

Buckets sort by event time when present, otherwise effective start, then domain and
exact reference kind/ID/revision. ordered_items provides the same deterministic global
display order without implying simultaneity or clinical priority. Source parameter,
organism, susceptibility and disclosure arrays retain declared order. Duplicate support
parameter identities are rejected. Snapshot validation checks bucket/domain pairing,
patient/encounter scope, duplicate refs and ingestion identities, repository UUID and
watermark bounds. Missing ingestion metadata requires a disclosure and establishes no
durable visibility claim. Registered ownership and source authenticity are not queried.

All models follow existing frozen, extra-forbidden, nested-revalidation conventions.
Mutable input lists are converted to tuples; caller mutation cannot change retained
content. Storage metadata is explicitly revalidated at this boundary. Trusted Python
model_construct/model_copy escape hatches still require validation at acceptance.

M2 gaps/deferrals: these are supplied recorded-state descriptors, not registered new
fact categories or lossless adapters from every existing PatientFact. Existing durable
facts support observations, medication orders/administrations and inferences; procedure
and condition domain models are not supported by current fact persistence. Generic
observations do not supply structured specimen/settings/susceptibility fields, and
existing medication contracts do not cover all stopped/changed/unknown-dose source
records. No mapping from free text, new event store, unit normalization or inferred
medication/antimicrobial classification is supplied here. M2 must define evidenced
mappings, preserve source linkage, and disclose unsupported data rather than fabricate
fields. Selection, availability policy, conflict handling, completeness, terminal
revision policy and explicit inference-input subsets also remain deferred. M1 neither
promotes every state item into lineage nor claims biological independence/adherence.

Focused tests: tests/test_patient_state.py. Classification:
MULTIDOMAIN CLINICAL STATE CONTRACTS ONLY. Kernel, persistence/schema, governance,
lineage and the completed weight/creatinine implementations remain unchanged.

## Multidomain Patient State v1 — M2.1 source-backed assembly

`patient_state_assembly.assemble_patient_state(engine, scope=PatientStateScope(...))`
returns an immutable PatientStateAssemblyResult after one existing repository
transaction exits successfully. SyntheticLaboratoryMedicationState version 1 reads
`list_latest_known(target=scope.target, cutoff=scope.repository_cutoff)` exactly once,
without time/ingestion filters, clock sampling or replacement cutoff capture.
Terminal visibility and M2.0 scope-before-decode validation precede all mapping.
No predecessor is resurrected when a terminal no longer maps or leaves the window.

Laboratory support is partial: observations must name synthetic-serum-creatinine,
source namespace clinrx.synthetic.serum-creatinine, version 1, and measurement or
external_record channel. A known Quantity is required by this numeric source shape.
All such terminal observations may be retained, including zero/negative values;
there is no cardinality, unit-conversion, positivity, verification or comparison
policy. Quantity/unit/source representations remain exact. Dedicated specimen and
result-status fields are absent from the durable model and remain absent/disclosed.
No creatinine capability code is imported or invoked.

Medication support covers durable orders and administrations. Orders retain dose,
route, frequency, schedule and source order_status. Administrations retain delivered
dose/route and their source type's completed-delivery meaning as administered.
Medication records are not classified as antimicrobial or support. This projection
is not a lossless copy of every fact field: exact source refs preserve access to
correction reasons and administration/order associations, which are not new lineage.
Source uncertainty is retained in labelled item disclosures, and provenance/time,
verification/conflict/status, binding and ingestion metadata are copied unchanged.

Point membership is closed [review_start, review_end], with explicit instant event
time and no time uncertainty. Missing/imprecise/uncertain point timing is unsuitable.
Orders with effective_start use inclusive overlap; absent end stays unknown and
never implies active therapy. Day/approximate recorded interval endpoints may be
used as representative bounds with explicit disclosure; unknown precision is
unsuitable. Event-first M1 ordering remains unchanged even for interval membership.
Availability by review_end is not asserted. Recorded/retrieved/processed and ingestion
metadata remain distinct, and captured_at never substitutes for an availability bound.

Exactly ten ordered DomainSourceCoverage entries accompany the snapshot. Laboratory
is partial, medication supported, and the other eight domains unsupported/not_attempted
with absent counts. Every source_completeness is unknown. Candidate counts count
unique terminal observations considered by the laboratory mapper (including unknown
concept/source profiles) or unique terminal medication orders/administrations.
Retained counts match bucket lengths. Unsuitable counts include supported-profile
shape/timing failures only; out-of-window and unsupported-profile exclusions are not
unsuitable. Thus candidate = retained + domain mapping issues; unsuitable is a subset
of those issues. Unsupported fact categories have unclassified profile issues and
are not counted as candidates in an invented domain.

Typed issues carry exact references, optional mapped domain and bounded reason codes,
ordered by reference kind/ID/revision then fixed reason order. Exact repeated records
are deduplicated only when canonical full fact AND ingestion metadata agree; conflicting
exact records or multiple terminal revisions in a supplied history result fail integrity.
Distinct equal-value facts remain distinct. Coverage and essential source/availability
limitations are mirrored into deterministic snapshot disclosures, including an omission
notice when issues exist. Empty never means clinically absent.

Public errors preserve bounded persistence categories, sanitize unexpected mapper/read/
transaction-exit failures as TransactionAborted, and preserve process-control exceptions.
Malformed storage never becomes an empty domain. There are no automatic retries.
The existing SQLite BEGIN IMMEDIATE policy still applies, including possible contention;
assembly performs no application writes and is not lock-free. Existing encounter-wide
history scanning is not a new bounded-resource/pagination guarantee.

M1 contracts, historical retrieval, shared transaction, schema, inference, lineage,
governance, execution/reconciliation and weight/creatinine implementations are unchanged.
Procedure/condition persistence, richer specimen/microbiology/support mappings and
contextual-history assembly remain deferred. M2.1 creates no clinical reasoning,
dependency graph or release decision. Focused tests: tests/test_patient_state_assembly.py.
