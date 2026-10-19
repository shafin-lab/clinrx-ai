# Bounded renal and fluid workflow specification

Draft for review, 19 October 2026. Baseline application:
`b4194447829f060387b816437694af9f6c0cb60e`.

**RF1 is a read-only synthetic renal/fluid review in the existing ICU patient
workspace.** Its purpose is to let a user inspect recorded creatinine and fluid
context together without creating competing records or new clinical conclusions.
This specification authorizes no implementation, policy change or execution.

## Intended user journey and completion boundary

Open the existing synthetic patient/encounter → open Renal and fluid review → inspect
serial creatinine with sample times/source context → inspect urine, fluid inputs,
losses, weight and renal-support context over explicit intervals → open exact source
and correction history → return to the same hemodynamics workspace and scope.

RF1 finishes when this one review path works against a real local API with exact
source/history correspondence and understandable missing/overlapping data. It does
not need a new inference engine, renal prescribing, hospital-wide modules or another
round of isolated hemodynamics demonstrations.

The existing hemodynamics authoring/comparison/handover workflow must continue to
work. RF1 does not pretend that generic laboratory facts already work in those
circulatory-only controls. Where a creatinine-to-note/handover action is unavailable,
show that capability as unavailable explicitly, rather than silently dropping the
selection or casting it into a circulatory record.

## Existing foundations and verified gaps

| Foundation in b419444 | Reuse and limitation |
| --- | --- |
| ClinicalObservation and immutable repository revisions | Store/retrieve existing serum-creatinine observations without inventing a circulatory creatinine type. Preserve raw fact digest, reference, binding and ingestion. |
| Creatinine trend backend | Existing synthetic selector/comparison/inference implementation; restrictive synthetic concept/unit/provenance profile. RF1 does not run it or expand its eligibility. |
| Patient State v1 | Laboratory and renal-support/fluid-output domain contracts exist. Existing product HTTP projection exposes laboratory/medication, not a complete renal/fluid product. |
| Patient State v3 | Bounded circulatory records with scope/cutoff, provenance and history. Its fact union is circulatory-only; it must not silently absorb generic observations. |
| Existing ICU fluid facts | CirculatoryEvent records already contain interval amounts, source-reported balances, urine totals, blood/IV inputs, drains and CRRT net removal. Reuse the same records; do not append copies as renal observations. |
| Weight and renal-support context | fs-WEIGHT is a source dosing-weight assertion, not proof of serial measured weight. fs-CRRT-NOTE is reported context, not proof of continuous treatment or full machine/settings data. |
| Current local authoring gateway | Allows circulatory reads/history and local CirculatoryRecord writes. It does not expose the generic laboratory state/history needed here. |
| UI and local handover | Shared state, source/history and exact-pin patterns are reusable. Current CirculatoryItem typing, guided fields and saved-pin decoder are not generic-observation support. |

## Scope

| Included in RF1 | Excluded |
| --- | --- |
| Serial recorded creatinine; exact original/corrected sample history; raw units and source timing | AKI diagnosis/staging, automatic trend inference/direction, eGFR, clearance, thresholds, alerts or treatment advice |
| Explicit urine-volume intervals, recorded IV/blood inputs, drains and renal-replacement net removal | New cumulative totals, rates, mL/kg/h, unit conversion, duration arithmetic or automatic fluid balance |
| Source-reported interval/cumulative balances, kept separate from measured amounts | Treating reported totals as verified complete reconciliation, or summing totals and their component events |
| Recorded weight with purpose/method/time when present; missing weight explicit | Deriving ideal/adjusted weight, dry weight, BSA or unrecorded weight changes |
| Existing renal-support context and source limitations | RRT prescriptions, machine integration, delivered-dose calculations, anticoagulation, dialysis recommendations |
| Common patient/encounter/repository/cutoff, read-only inspection and history | New renal write endpoints, mixed-kind reassessment/handover storage migration, authentication or durable command recovery |

No reference range, target, freshness threshold or clinical policy is invented.
Missing time is unplaced, missing amount is not zero, and missing support context
is not evidence that no renal support was delivered.

## Data and API design

1. Add an **opt-in local synthetic composite read** with a versioned DTO, provisionally
`SyntheticRenalFluidReview/v1`. Keep existing v1/v3 API response contracts unchanged.
2. Capture **one RepositoryCutoff** for one patient/encounter and review window.
Assemble both views explicitly at that cutoff using existing bounded repository
primitives. Do not join two independently refreshed endpoints that can have different
watermarks. This is a common historical view, not a claim of physiological simultaneity.
3. Retain the existing circulatory assembly/context intact, plus a bounded allowlisted
creatinine-observation collection with complete original facts, canonical digests,
ingestion and source context. Displaying a laboratory record is distinct from
eligibility for the existing creatinine inference profile.
4. Validate repository, patient, encounter, window, cutoffs, references, digests,
ingestion bounds, collection limits and duplicates at the transport boundary. Raw
fact digests, projected selection digests and typed payload digests are different
contracts; never substitute one for another.
5. Add bounded exact laboratory history tied to the composite signed context. It is
a read even if transported by POST. Require selected revision visibility at the
captured cutoff and exact scope; reject foreign, missing, malformed or ambiguous
references without fallback to the latest revision. The existing circulatory history
path retains its own signed-context contract.
6. The read gateway allowlists only the additive review/history paths. No preparation,
execution, renal write or reconciliation route is opened. The existing read-only
Docker gateway and production routes remain unchanged by default.
7. Shared UI state publishes the combined view only after correspondence checks.
Refresh clears active selections while retaining explicitly labelled historical
context; a mixed/failed response withholds the affected combined view. Preserve M1
repository isolation, mounted pending hemodynamic drafts and old request identities.
8. Apply existing row/history and response-size budgets across both collections;
do not silently increase caps or report complete coverage after truncation. A bound
failure is explicit, not a partial apparently complete renal record.

## Presentation rules

- Creatinine: one source sample per row, raw value/unit, recorded collection time
when supported, report/availability separately, exact reference/revision, source
verification/conflict/uncertainty and known specimen context. Never copy specimen
or time from a neighbouring sample or a value in narrative text.
- Timeline: keep source spelling/offset and precision. Use supported exact ordering;
ambiguous times remain ambiguous. No lossy timestamp coercion to place samples.
- Fluid/urine: draw/report explicit interval start/end independently of point events.
Show gaps, overlaps, partial intervals and unclear collection bounds as recorded;
no splitting or inferred hourly continuity. Recorded zero, missing and withdrawn
are visibly different.
- Event overlap: the existing 250 mL fluid challenge can be included in an interval
input row. Link its context without adding its amount again. Reported balances,
component inputs/outputs and cumulative totals are separate categories, never one
summed display value.
- Renal replacement: net patient fluid removal is not total effluent. Do not infer
replacement-fluid accounting, active treatment duration or treatment status from
an isolated CRRT volume/context record.
- Weight: retain its asserted purpose. A dosing-weight entry does not become a new
measured daily weight. Use explicitly separate source observations for future serial
weight examples.
- Source inspection: show exact selected historical content; do not replace a note's
or pin's evidence with a successor. Link the same source record from both modules.

## One synthetic episode and test fixture

Use synthetic-p1/synthetic-e1 in one repository. A new opt-in fixture factory can
compose the existing ICU fixture with a small explicit creatinine sequence and
negative-context examples. Do not seed on startup, mutate the accepted fixture or
modify the current user's database while preparing RF1. Do not create a separate
renal database with a competing patient history.

The new disposable fixture contains two distinct creatinine samples and a correction
of one sample, preserving the original. Supplement with missing sample context,
an unplaced time, unlike raw units and a withdrawn/suspect/conflicting example for
browsing tests. Existing urine/input/output/weight/CRRT chart entries are referenced
in place. A clearly marked gap/overlap example may be added as a separate synthetic
source record, not a generated balance. Exact values are fixture data, not clinical
thresholds or an approved inference policy.

## Planned implementation surface

These are proposed paths for a later authorized implementation. No files below are
modified or created by this specification.

| Existing surface | Planned bounded change or reuse |
| --- | --- |
| backend/app/demo/icu_flowsheet.py; icu_chart_entries.py | Reuse unchanged fixture factories/record identities; compose through a new opt-in fixture, not copies of existing facts. |
| backend/app/execution/patient_state_v3_assembly.py; patient_state_assembly.py; persistence/bounded_history.py | Reuse explicit-cutoff assembly/history and accounting. No change to inference/release semantics. |
| backend/app/services/circulatory_product_service.py | Reuse construction patterns/context issuance; avoid calling its self-capturing state method to create half of a separately captured composite view. |
| backend/app/demo/authoring.py; hosting.py | Existing defaults remain unchanged; a separate local gateway subclass opts into new read routes only. |
| frontend/src/demo/usePatientEvidenceState.ts; PatientWorkspace.tsx | Optional composite loader/state adapter, preserving existing circulatory component contracts, navigation and pending editor state. |
| frontend/src/demo/evidencePresentation.ts; flowsheetPresentation.ts | Reuse applicable display helpers; no fabricated CirculatoryItem casts for generic laboratory data. |
| frontend/src/api/client.ts; decoding.ts | Existing transport/schema-validation infrastructure; explicit additive read allowlist, without widening execution permissions. |

Proposed new files:

- backend/app/demo/renal_fluid_fixture.py
- backend/app/demo/renal_fluid_gateway.py
- backend/app/api/schemas/renal_fluid.py
- backend/app/services/renal_fluid_product_service.py
- frontend/src/api/renalFluidClient.ts, renalFluidTypes.ts, renalFluidDecoders.ts
- frontend/src/api/renalFluidSchemas.json and tools/export_renal_fluid_transport.py
- frontend/src/demo/RenalFluidReview.tsx and renalFluidPresentation.ts
- tests/test_renal_fluid_review.py and tests/test_renal_fluid_gateway.py
- frontend/tests/renalFluid.test.tsx and renalFluidDecoders.test.ts

Existing tests affected: frontend/tests/patientWorkspace.test.tsx and relevant gateway,
transport-schema drift and fixture tests identified during implementation. If the
change requires broad clinical-contract, schema/migration or inference redesign,
stop and revise this specification rather than expanding the milestone silently.

## Acceptance cases

| Case | Required outcome |
| --- | --- |
| RF1-01 shared episode | Renal and hemodynamic views show the same repository/patient/encounter/window/cutoff; mismatched replies fail closed. |
| RF1-02 creatinine history | Two samples remain distinct; a correction does not become a third sample or overwrite the original. Exact full history is inspectable. |
| RF1-03 context and units | Missing specimen/time and unlike units remain explicit; no source-time substitution, conversion or calculated trend is displayed. |
| RF1-04 intervals | Source urine/fluid interval bounds, gaps/overlap and zero/missing distinctions remain visible. No partial-interval prorating or derived hourly rate. |
| RF1-05 double counting | A fluid challenge, interval input and reported balance remain separate source assertions; no generated total double-counts them. |
| RF1-06 RRT and weight | Net removal versus effluent and dosing versus measured weight remain distinct; absent settings/status are not inferred. |
| RF1-07 historical safety | Withdrawn/corrected/foreign/out-of-cutoff evidence cannot silently become current selected evidence. Bounded history cannot fall back to a successor. |
| RF1-08 M1 and drafts | Repository changes require reselection; combined refresh cannot discard a pending hemodynamic draft or replace its original repository/request. |
| RF1-09 closed execution | New protected preparation/execution stays blocked. New read routes cannot expose arbitrary facts or renal writes. Existing receipts remain unchanged. |
| RF1-10 coherent use | One user can find a creatinine sample, inspect its correction and fluid context, explain a displayed gap and return to hemodynamics on desktop/narrow layout. |

## Validation and one review package

Use focused new service/DTO/history/gateway/decoder/UI tests for the acceptance cases,
plus existing affected hemodynamic navigation, M1, correction/recovery and handover
regressions. Run the full backend/frontend suites and both builds once on the final
candidate because the integration crosses transport and shared state; do not repeat
unchanged suites merely to publish evidence. Obtain exact-candidate hosted CI with
actual checkout identity. No test timeout or assertion relaxation.

Capture one browser-to-real-API read-only journey through the complete RF1 view,
actual response bodies with signed contexts redacted, source/build identity and
before/after database checkpoints demonstrating no fact/receipt writes. Retain exact
history, one representative uncertainty/interval inspection, desktop/narrow evidence
and a single indexed review package linked from PR 23. State whether operation was
assisted or uncoached. Old acceptance evidence supplies unchanged invariants only;
it cannot establish new renal endpoint or UI behavior.

## Separately authorized follow-on

RF2 may add structured renal entry/correction, exact mixed-kind authored notes and
saved handover. That requires an explicit allowed observation concept/unit contract,
strict local authoring DTO, a genuine mixed-kind evidence adapter and bounded history
resolver, and versioned handover compatibility. The current v1 pin decoder accepts
circulatory kinds only: do not broaden it silently or auto-rewrite old saved data.
Do not force an invented intervention into a renal review just to satisfy the old
three-selector note form. Define optional supporting context deliberately.

Any derived balance, normalized urine rate, creatinine interpretation or renal
support decision is a separate governed function with intended use, exact inputs,
limitations and approved rules. Existing synthetic creatinine inference eligibility
must not be relaxed to make a demo run.

Execution stays disabled. New additions remain frozen pending explicit implementation
authorization. No merge, deployment or external hosting is part of RF1 or this draft.
