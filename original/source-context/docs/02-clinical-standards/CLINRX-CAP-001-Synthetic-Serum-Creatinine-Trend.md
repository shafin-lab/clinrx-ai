# CLINRX-CAP-001 — Synthetic Recorded Serum-Creatinine Trend Review v1

Version: 1.0. Date: 2026-10-04. Status: implementation specification, synthetic only;
not implemented and not clinically validated. Kernel baseline:
`d52efb2b0d1759e432bf902cf5e3e65472c7e7aa`.
Related: [Kernel freeze](../01-architecture/CLINRX-KERNEL-001-Execution-Kernel-v1.md),
[extension guide](../01-architecture/CLINRX-KERNEL-002-Capability-Extension-Guide.md),
[DATA-001](../01-architecture/CLINRX-DATA-001-Clinical-Data-and-Knowledge-Standard.md),
[SAFE-001](../01-architecture/CLINRX-SAFE-001-Clinical-Safety-and-AI-Governance-Standard.md).
The parent standards remain Draft; this specification does not approve patient use.

## 1. Intended use and question

Synthetic review of a bounded historical serum-creatinine comparison; no diagnosis,
prediction, care recommendation, patient-care delivery or assertion of current clinical
eligibility.

Question: “Do two eligible retained serum-creatinine observations show a recorded
increase, decrease, or no change, and can that bounded historical finding be released
for review?” Direction describes recorded numbers only.

## 2. Reused kernel versus new policy

Reuse unchanged: ClinicalObservation, ClinicalInference, Quantity/Unit, Reference,
Binding, Provenance, ClinicalTime, canonical fact persistence, revision chains,
RepositoryCutoff, history and the generic durable lineage resolver. Reuse existing
snapshot/recommendation/safety/governance contracts and assess_release/decide_release.

New creatinine policy: selection, comparison, source/sample assumptions, method and
closed wording, producers/rules, final recheck, request/envelope/witness, later execution
adapter/table and reconciliation projection. No import of weight-specific types.

## 3. Concept and synthetic source contract

The one configured concept is `synthetic-serum-creatinine`; the v1 policy pins that
exact identity. It denotes a serum-creatinine measurement from a blood/serum sample
under the fixture contract only. No aliases, external mapping, assay harmonization
or reference-range interpretation. Other concept IDs are unrelated exclusions.

Eligible source records use namespace `clinrx.synthetic.serum-creatinine`, a nonempty
identifier naming one synthetic sample measurement, source version `1`, and channel
`measurement` or `external_record`. The fixture/source producer guarantees:

- One stable observation ID represents one sample measurement; corrections retain
  that stable ID and source namespace/identifier, with a reasoned supersedes link.
- Different eligible measurements represent different samples and have different
  source identifiers. Reimport of the same sample is not a new measurement.
- Sample time and result availability fields have the meanings in section 5.
- The producer supplies one finalized numeric result per sample, not a pending,
  censored, comparator-qualified or partial result.

The selector checks distinct stable IDs AND distinct source (namespace, identifier)
pairs. Duplicate sample keys among relevant terminal observations block selection,
including when their values agree. Distinct IDs alone do not prove distinct specimens.
The source version is format identity, not a substitute for observation revision.

ClinicalObservation has no dedicated specimen, assay, result-status or reference-range
fields. These fixture assertions are not a real LIS deduplication or specimen-verification
solution. Unknown/unsupported source semantics must not be silently treated as verified.
No model expansion is authorized in Phases A/B.

## 4. Unit and quantity policy

Only a known Quantity with finite Decimal value strictly greater than zero is eligible.
Quantity itself allows zero/negative finite values; the positive restriction is this
synthetic capability's input policy, not a clinical threshold or normal-range claim.
Zero, negative, text, boolean, missing or non-quantity results are ineligible; malformed
nonfinite stored quantities remain storage-integrity errors.

Require `Unit.raw == 'mg/dL'`, `system == 'UCUM'`, `code == 'mg/dL'` and status
`assessed` or `normalized`. Exact source spelling is required: no case/whitespace
normalization by this capability, no aliases, no missing/unresolved unit and no
µmol/L conversion. Existing domain parsing applies before these checks. A normalized
status does not authorize the capability to perform a conversion. Preserve Decimal
scale and retained values; no float arithmetic, rounding or calculated delta.

## 5. Three independent temporal boundaries

| Field/bound | Meaning |
|---|---|
| `time.event` | Specimen/sample collection instant, never result entry time |
| `time.recorded` | Source result recorded/available instant under the synthetic source contract |
| `time.retrieved` | Result received by the consuming system |
| `time.processed` | Result processed and available to this capability |
| `provenance.recorded_at` | Source assertion timestamp; in this fixture profile equals time.recorded |
| `available_at` | Explicit source/system availability bound for the original request |
| Repository cutoff | UUID + watermark controlling which revisions are visible; not an availability timestamp |

Require event, recorded, retrieved and processed to be present and aware, precision
`instant`, time uncertainty None, and actual-instant ordering
`event <= recorded <= retrieved <= processed`. Require provenance.recorded_at equal
to recorded by instant and binding.verification.assessed_at no later than available_at.
All availability times must be <= available_at (inclusive). Missing required fields
are typed eligibility issues, not fabricated timestamps. Effective-time fields are
not selection axes. Never use result-entry or ingestion time to replace sample time.

Policy requires `window_start < window_end <= available_at`; sample window is
`[window_start, window_end)`. Compare actual instants with exact integer arithmetic,
including offset-equivalent timestamps and DST folds; retain original offsets.
Two equal sample instants cannot form a valid comparison. Repository visibility and
availability checks must both pass; neither bound can substitute for the other.

## 6. Selection contract and deterministic behavior

`CreatinineTrendSelectionPolicy`: fixed id `CreatinineTrendSelectionPolicy`, version
`1`, configured concept above, fixed unit profile above, window_start/window_end and
available_at. Patient/encounter target and RepositoryCutoff are explicit selector
arguments and are retained in the result. Longitudinal selection is unsupported.

Use unfiltered `list_latest_known(target, cutoff)` first. Then classify terminals;
never search an older revision because its successor is ineligible. Eligible inputs
are observed/reported ClinicalObservation with matching concept and scope, verified
binding and fact verification `verified` or `clinician_confirmed`, conflict
`none_known`, complete provenance, no upstream declarations and no provenance
limitations, plus sections 3–5. Allowed observation uncertainty is empty or the exact
synthetic disclosure `synthetic uncertainty`; other wording blocks this closed profile.
Temporal status does not assert current eligibility and is not an additional filter.

For each terminal record, emit the first applicable reason in this order:

1. `unrelated_fact` for non-observation.
2. `unrelated_concept` for a different concept.
3. `invalid_or_missing_sample_time` for absent/imprecise/uncertain sample time.
4. `outside_sample_window` for sample outside the half-open interval.
5. `unresolved_conflict` for conflict other than none_known.
6. `unverified_input` for unsupported fact/binding verification.
7. `unacceptable_provenance` for source, origin, upstream, limitation or disclosure mismatch.
8. `invalid_value` for unsupported quantity/value.
9. `unsupported_unit` for any unit-profile mismatch.
10. `invalid_result_timing` for missing availability times or chronology/profile mismatch.
11. `source_unavailable_at_bound` for availability/binding verification after the bound.

The first two and outside_sample_window are benign exclusions. All other relevant
exclusions block a usable pair, even if two other eligible observations exist. Malformed
stored data and invalid request/policy/cutoff are exceptions, not ordinary issues.
Duplicate sample keys among same-concept, precisely timed, in-window terminal
observations add `duplicate_sample_measurement` issues for the colliding references;
check this independently of other eligibility failures. This does not choose a winner.

Preserve exclusion/per-input issue order by terminal ingestion sequence, with any
duplicate-sample issue after that record's eligibility issue. Count eligible observations
before global blocking: 0/1 adds `insufficient_eligible_inputs`; >2 adds
`ambiguous_eligible_inputs`; exactly two with equal sample instants adds
`invalid_measurement_order`. No latest-two shortcut. Any issue means selected=().
Otherwise selected contains exactly two observations ordered by sample instant.

Phase A selection failure returns typed issues; it does not manufacture a governance
decision. During a later final recheck of an initially successful request, selection
failure feeds withholding through governance.

## 7. Comparison and Phase A acceptance

`RecordedCreatinineComparison` fields are earlier_reference, later_reference,
earlier_value, later_value (Decimal), unit (literal `mg/dL`), earlier_sample_time,
later_sample_time and direction (`increase`, `unchanged`, `decrease`). Preserve exact
selected revisions, Decimal representation and timestamp offsets. Require distinct
stable measurements/sample keys through validated selection and strictly increasing
sample instants. Compare values directly: later greater/equal/less determines direction.
No absolute delta, percentage change, normality or rate-of-change significance.

Comparison accepts the validated successful selection only; an unsuccessful selection
returns its first typed issue without a result. Forged/reversed/duplicate inputs fail
validation. The result rejects inconsistent direction, invalid values and extra fields.
Selection/comparison perform no writes and are deterministic at the same cutoff.

## 8. Inference and Phase B acceptance

Use ClinicalInference unchanged. Method reference is
`inference_method:RecordedCreatinineTrend:1`. Inputs are exactly the earlier and later
observation references, in that order, with exactly two corresponding `derived_from`
edges and no extra dependencies. Origin is inferred, verification unverified, conflict
unknown and temporal_status unknown. Binding is retained from the earlier observation;
both inputs must share the verified requested patient/encounter scope.

Exact statement patterns (A/B use Python Decimal string representation, no rounding):

- Increase: `Recorded serum creatinine increased from {A} mg/dL to {B} mg/dL between the selected samples. Synthetic evaluation only; bounded historical comparison.`
- Unchanged: `Recorded serum creatinine was unchanged between the selected samples ({A} mg/dL then {B} mg/dL). Synthetic evaluation only; bounded historical comparison.`
- Decrease: `Recorded serum creatinine decreased from {A} mg/dL to {B} mg/dL between the selected samples. Synthetic evaluation only; bounded historical comparison.`

The unchanged pattern retains both representations even if equal Decimals have different
scales. Applicability is exactly `Synthetic serum-creatinine comparison within the selected patient/encounter and sample-time window only.`
Validation limitations are exactly `Not clinically validated; recorded values and synthetic sample identity only.`
Mandatory uncertainty, followed by deduplicated permitted input uncertainty, is:
`Recorded comparison does not establish clinical significance or cause.` and
`Synthetic evaluation only; specimen identity and input authenticity are assumed.`

Provenance source uses namespace `clinrx.synthetic`, identifier `RecordedCreatinineTrend`,
version `1`, channel `system`; actor is `RecordedCreatinineTrend/v1`. Lineage is complete
for declared inputs, with limitation `Synthetic evaluation only; no clinical validity or source-authenticity claim.`
Use caller-supplied aware executed_at >= available_at by actual instant for inference
event/recorded/processed and provenance.recorded_at. Leave target/horizon unset and
validation_references empty with the explicit limitation above. No prediction or care claim.

Builder revalidates comparison against the supplied selection, including canonical
Decimal/time/ref representations. It never queries latest or accesses the database.
Persist through existing append_fact, then resolve at a newly captured output cutoff.
Input cutoff cannot see the later inference. Reopen must preserve all fields exactly.
Later observation correction cannot substitute inputs within the retained inference;
a new execution may consume corrected evidence without mutating the earlier one.

## 9. Lineage and later retained witness

Use generic resolve_lineage unchanged. Phase B checks actual root, exactly two ordered
declarations/dependencies, evidence roles, ancestry, scope, metadata and disclosures.
Complete declared coverage is not source completeness or proven independence.

For later execution persistence, define CreatinineTrendLineageWitness separately:
root, target, cutoff, ordered declarations, node exact refs/ingestion metadata/payload
digests/roles/ancestry/lineage limitations, coverage and unresolved disclosures. It
materially strengthens retained evidence validation without duplicating fact bodies.
Pin the two-input graph; reject contradictory/extra structure rather than discard it.
No reuse of WeightTrendLineageWitness and no generic witness extraction yet. Missing
required evidence cannot support successful protected execution. Malformed graph is
an integrity error. No reverse graph, external-source graph or conversion nodes.

## 10. Later final recheck

Define `CreatinineTrendFinalRecheckPolicy:1` and separate typed recheck. Preserve
original policy/scope, require same repository and a nondecreasing prefix, and compare
original exact refs/digests with protected final selection plus consumed-inference
terminal status at that same final cutoff.

Material: changed exact selected refs (including same-value correction), final
selection failure/third eligible sample/duplicate sample/terminal ineligibility,
or consumed inference supersession. Same exact ref with contradictory payload is
an integrity failure, never ordinary withholding. Missing required original evidence
or impossible inference-family disappearance from a later valid prefix is operational/
integrity failure. A pure unavailable assertion cannot establish release.

Unrelated facts, out-of-window samples, harmless exclusions, execution insertion and
unrelated watermark growth are not automatically material. Keep original comparison
and inference; feed final-context adequacy/material change into unchanged governance.
Never manually rewrite a released decision as withheld.

## 11. Later governance and safety

Reuse ContextSnapshot, ClinicalClaim, ClinicalRecommendation, RenderedRecommendation,
SafetyEvaluation, ContentValidationAssertion, context/dependency assertions, RuntimeState,
GovernancePolicy, assess_release and decide_release unchanged. Snapshot is partial with
completeness_scope naming only this bounded comparison, never complete patient context.

New producers: creatinine snapshot/candidate/rendering builders, safety evaluator,
fidelity producer, historical context/dependency producers, final-context producer,
synthetic authority issuer and runtime assembler. Use distinct versioned identities
prefixed `SyntheticCreatinine` (including `SyntheticCreatinineFidelity/v1`,
`SyntheticCreatinineFinalContext/v1`, `SyntheticCreatinineProtectedExecution/v1`).
Required evidence and local implementation availability are checked, not assumed from
matching digest alone. No weight rule or producer identity is reused.

| Safety rule identity (version 1) | Evidence and failures | Does not establish |
|---|---|---|
| `creatinine_exact_evidence_and_input_suitability` | Exact selection/comparison, source/sample distinctness, unit/timing contract, inferred method/edges, real retained lineage, snapshot membership and disclosures. Contradictions or known unsuitable inputs are hard failures; missing required evidence is unavailable. | Real specimen authenticity, assay comparability, clinical validity |
| `creatinine_bounded_descriptive_output` | Independently derive direction/expected grammar from exact values; validate claims, rendering and complete disclosure payload. Extra/altered claims are hard failures; inability to establish meaning is unavailable. | Clinical significance, current eligibility or permission to deliver |

Both rules are required and non-overrideable. Specimen/unit suitability belongs in
the first rule, avoiding a redundant third rule. Operational storage/contract failures
escape the workflow rather than being converted into ordinary safety results.

Fidelity binds exact refs, both Decimal representations, sample times/offsets, unit,
direction, method, inference wording, applicability, uncertainty, limitations, candidate,
rendering and final payload. Sample times remain in structured comparison/snapshot
evidence; closed visible text does not invent another timestamp representation.
Unknown wording or clinical interpretation fails. Safety/fidelity expectations must
not be obtained only by calling the renderer under test.

Synthetic issuer `SyntheticCreatinineReleaseIssuer/v1` uses a distinct
`SyntheticCreatinineReleaseGrant:1` policy, intended use
`SyntheticHistoricalCreatinineComparison:1`, capability-scoped target/request/destination
and actor allowlist. A versioned local fixture grant must specify explicit validity
bounds; sample fresh authority after protected acquisition. No implicit authorization
from the weight issuer or its historical dates. Grant configuration is a required
later governance-phase input, not something Phase A/B invents. Expired/out-of-scope
authority withholds honestly. No production authorization is designed here.

## 12. Later execution, persistence and reconciliation

Separate contracts: CreatinineTrendSelectionManifest (including sample-key disclosures),
CreatinineTrendLineageWitness, CreatinineTrendFinalRecheck, CreatinineTrendReviewRequest,
and CreatinineTrendExecutionRecord. Request identity pins execution_id, complete target,
actor, original manifest, comparison, exact inference, lineage and requested_at; require
exact protected-workflow marker. Exclude generated final cutoff/recheck/decision,
finalized_at and ingestion metadata from request matching while validating their integrity.

Initially use a separate capability-specific execution table/adapter with canonical JSON,
digest, supported version, patient/encounter scope, immutable UUID and original UTC
ingestion metadata. Same-ID/same-content append recovers original metadata; different
content conflicts. Validate scope before payload decoding, detect corruption, and prove
reopen/process recovery. Execution rows do not enter clinical fact history/watermarks.
No table, migration or generic envelope is implemented by this specification.

Before this durable phase, minimally extend transaction composition so the existing
private lifecycle/Session/BEGIN IMMEDIATE can construct a creatinine adapter. Preserve
weight API behavior; no registry, raw handles, generic UnitOfWork or independent commit.

Future explicit reconciliation returns committed_match for retained released OR withheld
protected execution, or scoped absent. Incompatible identity conflicts; visible corruption
and operational failures raise. No current clinical recomputation. Explicit retry after
absence checks again and may evaluate changed evidence if still absent. Completion
uncertainty uses the existing typed exception. No automatic recovery wrapper or delivery.

## 13. Deferred scope

AKI diagnosis, KDIGO logic, eGFR, creatinine clearance, renal failure diagnosis, treatment
recommendations, renal dosing/drug adjustment, prognosis, urine output, multivariable
renal reasoning, reference ranges, abnormal flags, µmol/L conversion, LOINC, aliases,
assay normalization, specimen metadata expansion beyond synthetic assumptions, real LIS
integration, production authorization, API/frontend and delivery remain out of scope.
These terms are exclusions only and cannot appear as generated capability claims.

## 14. Future test matrix and phase gates

| Phase | Required independent evidence |
|---|---|
| A selection | Exactly two; 0/1; >2; relevant ineligible third; corrections and multiple corrections; no resurrection; wrong scope/concept/unit; zero/negative/nonfinite/text; unverified/conflicted facts; source profile/upstream; duplicate sample keys across distinct IDs |
| A timing | Start inclusive/end exclusive; availability inclusive at microsecond boundaries; collection vs result-entry ordering; missing availability; impossible chronology; offset-equivalent/equal instants; DST; future visibility independent of source availability |
| A comparison | Increase/decrease/unchanged; equal values with different Decimal scales; exact refs/sample times/unit; reversed/same-family/forged comparisons; no delta/extra fields; immutability, read-only SQL, deterministic reopen |
| B inference | Exact ordered inputs/edges/method; all three literal grammars; binding/uncertainty/limitations; no forbidden interpretation/target/horizon; tampered comparison rejected; no builder DB access; executed_at boundary |
| B durable lineage | Input/output cutoffs; exact reopen; A1+B1 pinned after A2; new A2+B1 run; graph corruption, extra/missing edges, roles, coverage/unresolved; immutable results; no writes during resolution |
| Later governance | Independent safety/fidelity oracles; unit/specimen/timing disclosure; required-check unavailability; fresh scoped synthetic authority; material-change through governance; released/withheld and operational failures distinct |
| Later execution | Single transaction/lifecycle; correction races with barriers; idempotency/conflict; corruption/privacy; commit-ack uncertainty; explicit reconciliation without DML/recomputation; absent then retry; process/hash-seed recovery |

Phase A acceptance: all selection/comparison contracts and failure boundaries above
are implemented without inferred clinical thresholds, kernel changes or writes.
Phase B acceptance: existing ClinicalInference persistence and generic lineage prove
exact historical pinning and reopening; no execution table or governance work is needed.
Run unchanged kernel/weight regressions alongside focused new tests. Later grant dates,
actors and adapter composition require their own scoped implementation task. No blocker
remains for synthetic Phases A/B under the explicitly restricted source contract.
