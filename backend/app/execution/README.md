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

A recovered record is historical evidence. Final context checks, release decisions
and execution persistence are not yet one protected transaction. Increment 3 still
owns that composition and its race/commit/recovery guarantees; storage alone does
not establish continuing release eligibility, presentation or delivery.
