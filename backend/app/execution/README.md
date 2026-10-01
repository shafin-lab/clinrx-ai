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
