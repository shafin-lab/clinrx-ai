# Synthetic recorded-weight contracts — Sprint 7B.1 Phase 1

`weight_trend.py` selects and compares retained observations only. No inference,
release, rendering, execution-record storage or clinical validation is performed.

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
This phase does not construct a ContextSnapshot, resolve durable lineage, certify
selection history submitted by callers, or establish release eligibility.
