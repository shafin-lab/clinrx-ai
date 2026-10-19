# M1 through M7 reuse and duplication review

Reviewed against application `5cb73212ae6104b02bad361886cd9507795d88bf`, tree `7505ff88af8089f2d729fc230b15f3a604c5c9c0`, 19 October 2026. This maps the existing source contracts and workflows relevant to RF2. The accompanying source inventory records inspected file hashes and Git blob identities. It is not a line-by-line audit of every implementation file or proof that every upstream real-world duplicate can be detected.

## Conclusion for RF2

Creatinine, weight, source history, immutable corrections, bounded retrieval, execution recovery and hemodynamic charting already have foundations. RF2 must reuse them. Its new work is the missing local renal charting, explicit mixed-kind reference adapter and versioned handover integration. It must not create a second creatinine engine, weight ledger, fluid store, repository, patient identity or inference/recovery engine.

M1–M5 below are the recorded milestone scopes from the recovered roadmap, not newly invented clinical-module titles. Kernel v1 and the early creatinine extension remain shared foundations outside that numbering. RF2 contributes to M8/M9; their workflows were not already completed by the existence of earlier typed domains.

## Existing capability and reuse decision

| Existing work | Inspected foundations | RF2 decision |
| --- | --- | --- |
| Kernel and recorded-weight capability | models/clinical/common.py and facts.py; persistence/repository.py and bounded_history.py; execution/weight_trend.py and weight_trend_workflow.py | Reuse facts, units/missingness, exact references, history and transactional identity. Existing weight selection/inference is not a measured-weight charting form and stays inactive. Do not invent another source weight because a new screen needs it. |
| Early creatinine extension | execution/creatinine_trend.py and creatinine_trend_workflow.py | The existing synthetic-serum-creatinine concept and governed synthetic review remain the owners of those semantics. RF1/RF2 read the original observations; no new trend algorithm, eligibility relaxation or parallel creatinine facts. |
| M1 typed multidomain state | execution/patient_state.py | Laboratory, renal-support, fluid-output and other domain types already exist. Reuse compatible contracts. A defined domain type is not proof of complete charting/API coverage; avoid rebuilding the type system or claiming those workflows are finished. |
| M2 historical ownership and assembly | execution/patient_state_assembly.py; persistence/repository.py and bounded_history.py | Reuse terminal-history selection, ownership and cutoff/budget rules. V1's fixed mapping supports a narrow laboratory profile and medication, with unsupported coverage elsewhere. RF2 must not force missing/unplaced renal evidence through a projection that excludes it. Add bounded adapters only where needed. |
| M3 A/B/M temporal relation | execution/patient_state_inference.py | Preserve the existing laboratory/laboratory/medication inference unchanged. A renal note is authored text, not another inference or a reason to force an intervention selection. |
| M4 execution and reconciliation | execution/patient_state_execution.py and patient_state_workflow.py; persistence/shared_transaction.py | Preserve retained receipts and shared transaction/uncertainty semantics. Local evidence saves are separate from governed clinical execution. Reuse exact request/lookup/retry patterns, not a newly designed automatic retry engine. |
| M5 product APIs and demo | services/patient_state_product_service.py; api/routes/patient_state.py; frontend/src/api/client.ts and App.tsx | Reuse scope checks, transport bounds and application composition. Legacy and comprehensive views are versioned presentations, not separate ownership of laboratory facts. Do not remove accepted interfaces merely because they resemble a newer screen. |
| M6 microbiology and antimicrobials | models/clinical/microbiology.py and antimicrobials.py; execution/patient_state_v2.py, patient_state_v2_assembly.py and patient_state_v2_inference.py; services/micro_antimicrobial_product_service.py | Preserve culture/specimen/isolate/susceptibility and antimicrobial pathways. An antimicrobial order, administration and a fluid carrier volume are distinct source assertions. RF2 must not recreate medication orders or infer fluid volume from drug dose. Link an explicitly shared upstream record where supported; otherwise show unresolved accounting rather than duplicate or sum it automatically. |
| M7 hemodynamic evidence | models/clinical/hemodynamics.py; execution/patient_state_v3.py and patient_state_v3_assembly.py; services/circulatory_product_service.py; demo/icu_chart_entries.py and icu_flowsheet.py | Reuse existing urine/fluid events, source totals, dosing-weight support, CRRT context and exact associations. Infusion-series IDs intentionally recur across events and pump records; they cannot identify a unique measurement. New RF2 entry must not copy these facts. |
| Later M7 local workflow and RF1 | demo/authoring.py; services/renal_fluid_product_service.py; frontend/src/demo/usePatientEvidenceState.ts, EvidenceEntryWorkspace.tsx, ReassessmentComparison.tsx and localHandover.ts | RF1 composes raw creatinine and the existing circulatory assembly at one cutoff; shared UI state reuses its circulatory view. Reuse correction/recovery and comparison controls through explicit adapters. Renal mixed-kind note resolution and handover v2 are genuine gaps; don't silently broaden v1 or cast generic observations to circulatory items. |

Backend paths above are relative to backend/app; frontend paths are explicitly named. The source inventory makes each path unambiguous.

## Concrete shared records in the existing synthetic episode

The saved redacted API capture from the prior accepted-build local update has 164 circulatory items and four creatinine terminal observations: 168 distinct exact kind/ID/revision tuples. This establishes uniqueness of those exact references in that captured composite, not the absence of semantic duplicates under different identities or a new runtime observation.

- `observation/demo-creatinine-A/2` is the correction of the original sample's revision 1. The same sample appears in renal review without cloning it. The other existing terminal observations are demo-creatinine-B/1, rf1-creatinine-missing/1 and rf1-creatinine-unlike-unit/1. Baseline demo/patient_state.py creates the original laboratory samples; RF1 adds a revision and negative-context examples explicitly.
- `circulatory_event/fs-WEIGHT/1` retains 70 kg of source dosing-weight context. Existing infusion delivery records reference that exact weight. Source wording about actual weight does not supply a new independent typed acquisition-method assertion. RF2 must preserve unavailable acquisition metadata rather than infer measured status from dosing use or prose.
- `fs-FLUID-CHALLENGE`, interval input/output rows, `fs-URINE-TOTAL` and `fs-BALANCE-TOTAL` already exist. A challenge may be included in an interval input; a reported total may overlap its components. These are separate source assertions and are not automatically additive.
- Existing generic recorded-weight capability uses ClinicalObservation and an explicit concept policy; the inspected weight tests use body-weight. That demonstrates a supported foundation, not a production terminology mapping or proof that such a weight is populated in this episode. RF2's inventory must identify actual supported concepts/owners before exposing them.

## Repetition that is legitimate and duplication to prevent

| Pattern | Treatment |
| --- | --- |
| One exact fact displayed in several module views | Expected reuse. Maintain the same repository, identity, revision, digest and historical cutoff context. |
| One measured weight referenced for dosing and renal review | Keep one quantity. Acquisition and purpose are independent; retain the additional purpose as context without changing acquisition. |
| A separately asserted dosing value or another genuine collection | Retain the distinct assertion and provenance. Do not silently replace it with the measured weight or merge equal numbers. |
| One upstream source record submitted again with fresh local IDs | Match the scoped source-record/component key and exact material content; return the original retained result without a new row. After correction, disclose supersession without restoring the original as current. |
| A shared collection, infusion-series or device ID | Context only unless the source contract supplies an unambiguous record/component discriminator. Never collapse events on this key alone. |
| General medication and specialised antimicrobial/vasoactive records | Related contracts with different meanings, not proven duplicates. A future ingestion ownership map must resolve shared upstream identity before linking or reconciling; RF2 must not introduce another medication entry path. |
| Similar v1/v2/v3 assembly and product-service code | Versioned contracts and separate clinical scopes. Reuse established helpers where compatible; no broad refactor or automatic union merge in RF2. |

## Required implementation boundaries

1. Before RF2 coding, map source record/component keys, concept/category allowlists, acquisition/purpose fields and original correction ownership. Treat this audit as the capability map, not a completed issuer integration contract.
2. Prove structured metadata and exact note pins fit existing bounded carriers. Otherwise return a specification amendment; do not add clinical models/storage silently.
3. Reuse shared repository transactions, bounds, canonicalisation, exact tuple identities, duplicate-member rejection and pending-request recovery. Keep clinical execution disabled.
4. Demonstrate zero new source rows when adding an existing weight/fluid fact to another view, reassessment or handover; only the explicitly saved note may be new. Genuine new measurements and corrections require their declared write ledger.
5. Test two issuers with the same literal ID, multiple components in one collection, shared series IDs, fresh local request replay and replay after correction. Ambiguity/multiple matches/budget failure must not become insertion permission.
6. Keep acquisition (measured/reported/unknown), acquisition method and intended purpose separate. Test measured-for-dosing reuse, a separate dosing value and historical unavailable acquisition metadata.

No new deterministic application defect or repair is claimed by this source review. There are integration risks that RF2 must address, and existing capabilities that RF2 must not rebuild. No application tests, database mutations, clinical executions or application changes were performed for this audit.
