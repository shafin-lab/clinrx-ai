# M7-B — Recorded circulatory evidence

Synthetic backend capability. Not clinical approval or patient-care authority.

## Implemented boundary

`models/clinical/hemodynamics.py` declares 15 independently revisioned fact kinds:
pressure, cardiac performance, volume-related measurements, dynamic measurements,
source-device HPI, perfusion, oxygen transport, lactate, echo, ECG, vasoactive events,
monitoring events, dynamic assessment episodes, contextual events and signal manifests.
Each kind has explicit typed concepts or discriminated event/result payloads. There
is no free-form clinical JSON payload, clinical calculation or diagnosis engine.

All these kinds have explicit durable admission in `m7_0008`. Source-reported Edwards
and PiCCO parameters can be stored and reconstructed with their declared technology,
configuration, source parameter, mapping assertion, algorithm, quality and units.
There is no universal manufacturer capability matrix: product names do not establish
parameter availability. Source-documentation assertions remain attributed evidence,
not validated manufacturer compatibility. HPI is retained proprietary source output;
ClinRx neither calculates it nor uses it as a treatment trigger.

Echo/ECG findings and dynamic-test interpretations are source-reported only. Full
imaging, ECG interpretation, device ingestion and numerical clinical calculators are
not implemented. M9 owns future fluid balance; M14 owns broader imaging truth.
Mechanical support operation and management remain deferred, not infusion variants.

## Patient State v3

`patient_state_v3.py` and `_assembly.py` define profile
`RecordedCirculatoryEvidence:1` and contract version 3, separate from v1/v2 and
from governance ContextSnapshot. Closed observation-review boundaries retain exact
end instants. Lactate placement uses collection, never report/availability time.
Missing time remains unplaced. Bounded times use declared bounds for overlap.
Ordering uses actual event instants then exact reference identity; offsets and
Decimal scale remain in canonical payloads. Supplied source timestamp lexemes and
attributed alternative time assertions are retained. Recorded clock alignment, offset,
drift and uncertainty never trigger automatic timestamp correction. No interpolation or rate carry-forward.

H1-B pre-decode admission counts all visible candidates before selecting terminal
families or filtering. The assembler follows bounded exact associations, exposes
historical/unavailable/foreign targets according to repository semantics, and never
substitutes a predecessor. Withdrawn/invalid terminal evidence remains visible with
an issue and is unsuitable for inference. Coverage never establishes source
completeness, clinical absence or continuous physiology.

Limits cover history rows/bytes, per-family reads, aggregate reads, items, groups,
relationships, contextual items, fanout/depth/steps, manifests, issues and serialized
bytes. Exhaustion is QueryLimitExceeded, not successful withholding or truncation.
M7 execution payloads are limited to 16 MiB, with scoped byte admission before
payload materialization/decoding, including reconciliation. SQL scan time is not bounded by this.

## Approved first inference policy

Method `RecordedPressureLactateVasopressorTiming/v1` is a pure function over a
validated assembly plus exact named pins and digests. It samples no clock and
performs no repository reads or writes.

P: recorded systemic systolic, diastolic or mean pressure; invasive arterial or
automated cuff; source mmHg (or explicitly assessed UCUM mm[Hg]); numeric uncensored
result; acceptable quality and no artifact. Invasive acquisition requires attributed
adequate calibration and zeroing. Cuff zeroing is not required. Monitor MAP is
accepted as source output when provenance/configuration/mapping is explicit; no
ClinRx MAP is calculated. Known conflicting anatomical compartments are unsuitable.

L: quantitative uncensored mmol/L lactate, final report, exact collection assertion
or specimen identity. Final corrected/amended terminal reports qualify. Missing,
preliminary, pending, cancelled, withdrawn and unknown reports do not. Negative
concentrations are unsuitable. Reporting time never replaces collection.

V: actual documented initiation with delivery attestation, exact event time and
mapped identity. Orders, preparation, rate changes, restart and stop cannot substitute.
The initial identity spellings supported for inference are norepinephrine,
epinephrine, vasopressin, phenylephrine and dopamine under identity version 1;
broader agents including dobutamine and milrinone remain persistable. No terminology
matching, equivalence inference, dose conversion or continuous-exposure claim exists.

Selected clinical times require explicit verified clock provenance, exact precision,
no unresolved contradictory instant and no free-text uncertainty. Declared unknown
or unsynchronized alignment and known nonzero offset/drift/uncertainty are unsuitable
for exact ordering; source timestamps are never automatically adjusted. Offset-equivalent
assertions agree. Known future source availability/event/recording is unsuitable.
Bindings must be verified and scoped. Missing clock information is not synchronization.

P/L/V inputs and derived_from edges retain that role order. Independently consumed
support is explicitly pinned afterwards in exact-reference order. Calibration,
zeroing, device and delivery bindings and used provenance dependencies cannot be
hidden. Unsupported external specimen dependencies abstain rather than pretending
that a microbiology-specific specimen is a universal laboratory record. Embedded
collection assertions permit the self-contained three-input path. Unrelated order,
context or dosing-weight links are not timing evidence.

The fixed statement reports P acquisition, L collection and V initiation timestamps,
then P-versus-V and L-versus-V before/at/after relationships. There are no diagnoses,
threshold classifications, effects, dosing advice, causal claims or treatment plans.

## Protected execution and recovery

`patient_state_v3_execution.py`, `_release.py`, `_workflow.py` and
`persistence/circulatory_executions.py` are dedicated capability contracts/producers.
They use generic assess_release/decide_release unchanged. The existing shared owner
adds one concrete adapter; it retains one Session/BEGIN IMMEDIATE, poisoning, rollback,
completion ownership and post-exit invalidation. No new transaction manager exists.

Inference must already be persisted. New execution replays original assembly and
reconstructs the exact inference, then captures retained original and terminal
witnesses in the protected transaction. Any selected/support/inference successor is
material, including same-value or provenance-only revisions. Independent new facts
do not invalidate a statement restricted to the exact selected events.

The synthetic grant has dedicated M7 identities and the fixed test window
2026-10-08T12:00:00Z through 12:05:00Z (end exclusive), synthetic-p1/e1 only. It is
not authentication. Released/withheld receipts retain decisions and original evidence.
No API, display receipt or actual delivery claim is added.

Exact scoped receipt lookup precedes clinical reads, clocks and accounting. Retry
and reconciliation share one canonical request matcher. Reconciliation only loads
retained content: no assembly, inference, clocks, governance producers, DML or
execution. committed_match retains both released and withheld outcomes and original
metadata. Foreign scope remains absence; conflicting request or visible corruption
raises. Absence is a lookup result, not proof of rollback or permission to auto-retry.
An explicit later retry rechecks the retained row before new work. CompletionUnknown
semantics and SQLite lock policy remain unchanged.

## M7-C dependencies and deferred work

Backend contracts, persistence, bounded assembly, first inference and protected
execution/reconciliation are the M7-B boundary. Signal data, external fluid/imaging
references and recorded source assertions are reference-only where stated above.
No waveform samples are manufactured or stored as separate revisions.

M7-C must add a scoped application service, capability-purpose command/state envelopes,
strict DTOs and runtime decoders for all five response paths, retained provenance
projection and clinician review UI. Preserve H1-D uncertainty behavior, exact command
and UUID, explicit reconciliation, late-response protection and no automatic execution.
No M5/M6 route, transport schema, frontend or existing clinical policy is changed here.
