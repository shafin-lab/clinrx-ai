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
