# Bounded M6–M10 Corrections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Complete a simple integrated desktop review across M6–M10 while preserving all existing work and patient data.

**Architecture:** Retain the modular application and source owners. Align exact component/review/read contracts, add a small respiratory evaluation resolver and retain dose-review context, with focused presentation/recovery corrections.

**Tech Stack:** Existing React 19/TypeScript/Vitest, Python 3.11/FastAPI/Pydantic/SQLAlchemy/pytest; no new dependencies.

**Spec:** `/private/tmp/clinrx-bounded-m6-m10-20261025/docs/superpowers/specs/2026-10-25-bounded-m6-m10-corrections-design.md`

## Global Constraints

- Work only in `/private/tmp/clinrx-bounded-m6-m10-20261025`; preserve original worktrees, plans, sources, previews and patient data.
- Keep ports 5243, 5244 and 5245, their served builds, databases and signing material unchanged. New preview uses a copied synthetic database, separate build and loopback origin on port 5246 if free.
- Relevant records appear automatically. No generic reuse button, second source write, or repeated entry to display existing evidence.
- Blood products remain visible and counted through the existing `input_blood` owner/link. Do not alter product/fluid arithmetic, create intake from viewing M10, or add a linked M10 volume again.
- Keep clinical execution disabled, M7-C gated, reference JSON unreviewed/non-executable, all dosing formulas/rows unchanged, and source/calculation eligibility qualifications intact.
- Do not mutate historical canonical payloads through new default model fields. Optional additions must retain the old canonical serialization when absent; test this explicitly.
- No live hospital integration, external order, remote push/merge or clinical activation. Mobile and M11 are deferred.

## Review Focus

- A same numeric value in distinct specimens/kinds remains distinct; duplicate exact projections appear once (Task 1).
- Later or ambiguous support cannot replace gas-time FiO2, nor rescue a suspect own-record value (Task 3).
- Unknown-availability terminal correction at the shared cutoff still holds older positive M10 claims (Task 2).
- New optional source/request fields cannot change legacy canonical bytes or exact retry (Tasks 3/4).
- Damaged/stale draft recovery cannot overwrite bytes, submit under another scope or duplicate a confirmed save (Task 5).

## Task 1: Exact contributors and consistent renal review identity

**Files:** create `frontend/src/clinicalEvidence/componentIdentity.ts`; modify `frontend/src/renal/RenalInvestigations.tsx`, `renalBedsideModel.ts`, `RenalBedsideReview.tsx`, `frontend/src/respiratory/reviewEvidenceContext.ts`, `frontend/src/demo/PatientOverview.tsx`, `frontend/src/transfusion/model.ts`; tests `frontend/tests/renalInvestigations.test.tsx`, `renalBedside.test.tsx`, `transfusionModel.test.ts`.

**Interfaces:** produce `componentIdentity(e:Evidence,component:string):string` and `RenalSourceSelection {keys:string[];group:RenalGroup;label:string}`. `RenalInvestigations.onOpen(selection)` passes the exact counted keys. Produce `m8ReviewEvidence(state,requested,catalog?)` with the same `{signature,identity,pins}` contract as M7; module and overview consume the same matcher.

- [ ] Write failing regressions: BUN-only and abbreviated K labels open exact counted entries; urine opens Urine; supported total calcium is not disconnected; site-unknown iCa is not systemic; final/invalid source is visibly invalid; cross-kind same-ID M10 lab rows survive; repeated exact entries yield one row; M8 same-cutoff changed coverage/pins is historical, token rotation alone stable; queued-save changed evidence blocked.
- [ ] Run focused tests and retain expected red output.
- [ ] Implement the exact selection/status/identity changes. Use complete source keys and original flags; preserve legacy notes/history and daily-fluid window exclusion. Add no new lab concepts or clinical calculations.
- [ ] Run focused tests, full frontend suite with four workers, typecheck; report any failure by name.
- [ ] Commit only task paths and report base/head, tests and residual limits.

## Task 2: One bounded M10 snapshot for overview and detail

**Files:** modify `backend/app/demo/transfusion_gateway.py`, `backend/app/services/transfusion_service.py`, `frontend/src/transfusion/types.ts`, `client.ts`, `TransfusionWorkspace.tsx`, `model.ts`, `frontend/src/demo/usePatientEvidenceState.ts`, `PatientWorkspace.tsx`; tests `tests/test_m10_backend.py`, `test_m10_review_regressions.py`, `frontend/tests/transfusionClient.test.ts`, `transfusionWorkspace.test.tsx`, `transfusionModel.test.ts`, `m10Integration.test.tsx` and shared-loader tests as necessary.

**Interfaces:** `M10Transport.catalog(start:string,end:string,scope?:{repository:string;cutoff:number}):Promise<M10Snapshot>`; shared loader produces `m10:{snapshot?:M10Snapshot;loading:boolean;error?:string}`. Both M10 view components accept optional shared read and do not fetch their own catalog when supplied. Standalone clients retain optional-scope compatibility. Consume Task1's `laboratoryProjection(catalog):{rows:LaboratoryRow[];valid:boolean;error?:string}`; conflicting same-identity laboratory content is visibly unconfirmed and cannot enable interpretation/actions or look like true absence.

- [ ] Write red backend cases for valid bounded snapshot, repository mismatch, future/negative/partial cutoff, later correction exclusion, unknown-availability terminal hold at selected cutoff. Write frontend regressions for one loader-owned read, navigation without another semantic fetch, M10 failure isolated from other confirmed systems, stale reply suppression, one shared refresh after save and visible laboratory-projection conflict rather than an empty-normal result. Known typed coagulation/calcium concepts remain included when original labels are abbreviated, while raw labels and conservative unknown-label matching stay intact.
- [ ] Verify the failures occur for the missing behavior.
- [ ] Add paired query validation and bounded service reading. Preserve unknown-source, history and accounting behavior. Integrate one loader-owned snapshot, retaining all current patient/gate/cutoff checks and standalone component tests.
- [ ] Run focused frontend/backend cases, full frontend suite, typecheck and the full backend suite with `PYTHONPATH=backend`.
- [ ] Commit only task paths; report signatures and evidence.

## Task 3: Respiratory support/sample resolution, mode semantics and non-repetitive review

**Files:** create `frontend/src/respiratory/respiratoryEvaluation.ts` and `ventilatorModes.ts`; modify `respiratoryTypes.ts`, `physiology.ts`, `RespiratoryWorkspace.tsx`, `RespiratoryEntry.tsx`, `respiratoryCatalog.ts`, optionally `RespiratoryBedsideOverview.tsx`; backend `backend/app/models/clinical/respiratory.py` only for optional acquisition metadata with legacy serialization retained; regenerate existing transport schema only if needed. Tests `frontend/tests/respiratoryPhysiology.test.ts`, `respiratoryWorkspace.test.tsx`, `respiratoryModel.test.ts`, new `respiratoryEvaluation.test.ts`, `tests/test_respiratory_contract.py`, `test_respiratory_gateway.py`.

**Interfaces:** produce `resolveRespiratoryEvaluation(sample, catalog):{inputs:ReadonlyMap<string,{measurement:RespiratoryMeasurement;source:Evidence}>;issues:string[]}` for missing FiO2 only under Spec C. Extend `calculateRespiratoryPhysiology(record, evaluation?)` without rewriting `record`; every external input description carries exact source/component/revision/digest. Produce `ventilatorModeProfile(raw:string|null)` returning versioned recognition/parameter hints, preserving raw wording and unknowns. Optional acquisition metadata carries channel plus acquisition/interval identity; choose compact names and document them before changing types.

- [ ] Write failing cases for gas at09:00 plus exact linked usable support09:00, later support09:05, two eligible linked supports, wrong encounter, stale revision, unknown time, suspect own FiO2 and no explicit sample confirmation. Assert original objects/canonical source unchanged and source pins included in output.
- [ ] Add red mode/channel cases: VC–AC recognized under existing valid hold/flow conditions; unsupported/mixed/adaptive mode held for resistance; generic Vt/RR with absent or mismatched channels cannot yield minute/alveolar estimate; compatible explicit channel/acquisition may calculate; target/delivered separate; unknown mode still permits unrelated eligible arithmetic.
- [ ] Add red legacy canonical round-trip and exact-reimport assertions for omitted metadata, plus persisted fields when explicitly supplied. No new default field may alter prior bytes/digests.
- [ ] Add UI red cases for automatically visible support context, no reuse action, one primary gas table, detailed measurements on demand, exact remembered sample after reload and stale selection after correction. Preserve existing ABG/PFT qualification tests.
- [ ] Implement Spec C's strict resolver and modes/metadata. Preserve source role/quality/unit/static-condition gates; increment eligibility version. No chemistry/CO automatic pairing, new formula or support episode engine.
- [ ] Run focused cases, full frontend suite, typecheck and full backend suite; commit/report only task paths.

## Task 4: Existing renal inputs and retained antimicrobial decision context

**Files:** modify `frontend/src/antibioticWorkflow/CreatinineClearance.tsx`, `RenalDoseAdvisor.tsx`, `renalDoseModel.ts`, `AntibioticWorkspace.tsx`, `AntibioticRecordEditor.tsx`, `CultureReview.tsx` or `AntibioticOverview.tsx` for qualified therapy text, `frontend/src/api/antibioticClient.ts`; backend `backend/app/api/schemas/antibiotic_chart.py`, `backend/app/services/antibiotic_chart_service.py` only as needed for bounded provenance, existing generated antibiotic transport schema. Tests `frontend/tests/antibioticWorkflow.test.tsx`, `antibioticCorrections.test.tsx`, `renalDoseModel.test.ts`, `tests/test_antibiotic_chart.py`.

**Interfaces:** `PrescriptionSeed` gains optional `doseReview` with a typed bounded candidate-provenance object: version, profile/source, original suggestion, arithmetic inputs/result, selected renal/culture context and evidence/source references. `AntibioticDraft` may retain corresponding optional `dose_review`; serialize it only when present to preserve historical request canonical bytes. Expose `recordedClearanceInputs(catalog)` as a pure selector returning optional weight/creatinine plus exact sources and reasons; it never writes observations.

- [ ] Red cases: one eligible recorded Cr/weight appears automatically with source/time; ambiguous/unknown/incompatible values do not auto-select; manual edit not overwritten on render; changed source invalidates calculation/suggestion; four-input form retained.
- [ ] Red handoff cases: original inputs/profile/source/culture/renal scope survive draft, validate/save/reload and correction; editing final dose does not alter retained suggestion context; blank/manual draft has none; cancelled culture selection cannot leak. Existing uncertain-save exact recovery cases stay green.
- [ ] Red backend cases: old no-provenance canonical/retry unchanged, bounded optional context retained, invalid/oversized context rejected without writing, stale/mismatched provenance never treated as validated policy. No new dose rows or eligibility relaxation.
- [ ] Implement automatic supported inputs and candidate decision context. Keep age/coefficient explicit and separate renal support gates. Qualify recorded therapy status rather than adding an order-lifecycle service.
- [ ] Run focused cases, frontend suite/typecheck, full backend suite; regenerate schema with the repository's existing exporter if needed. Commit/report only task paths.

## Task 5: Presentation continuity and recoverable M10 drafts

**Files:** modify `frontend/src/hemodynamics/M7BedsideReview.tsx`, `frontend/src/respiratory/SharedPatientContext.tsx`, `frontend/src/demo/PatientWorkspace.tsx`, `frontend/src/demo/PatientOverview.tsx` for calculation-limit copy only, `frontend/src/transfusion/Entry.tsx`, small `draftRecovery.ts` helper if needed; tests `frontend/tests/hemodynamicBedside.test.tsx`, `m7SharedWorkspace.test.tsx`, `transfusionWorkspace.test.tsx`, `transfusionCorrections.test.tsx`, integrated workspace tests.

**Interfaces:** a pure draft decoder distinguishes absent/valid/damaged with retained raw bytes, and separates stable patient/owner recovery identity from changing evidence identity. Do not change `M10Command` pending recovery or accounting. Existing compact vital/echo/BP/PFT/ABG surfaces are binding.

- [ ] Red cases: primary results not redundantly expanded while source/trend access remains; relevant contextual records automatic across navigation; review wording matches browser persistence; overview limitations describe available qualified arithmetic truthfully rather than saying all automated calculations are inactive or that CrCl is manual-only; source inspection does not create writes.
- [ ] Red recovery cases: malformed session draft bytes remain byte-identical after mount/edit attempt; safe discard explicit; exact same patient/owner recovery across evidence refresh is visible but stale save held; wrong patient/repository/predecessor not hydrated; confirmed receipt survives refresh error; pending command continues original lookup/retry.
- [ ] Implement minimal progressive disclosure and protected session-draft handling. Avoid another navigation system, compulsory acknowledgments, or data-entry controls.
- [ ] Run focused tests, full frontend suite, typecheck. Commit/report task paths.

## Task 6: Frozen combined verification and independent review

**Files:** durable evidence under project `connected-overview-candidate/review-evidence/bounded-m6-m10-20261025/`; update the task ledger and documentation only. Root owns runtime/build/DB operations.

- [ ] Run frontend full suite four workers, backend full suite correct path, typecheck, whitespace and seven-flag build to a new immutable directory. Record complete outputs, warnings and exact commit.
- [ ] Copy the existing synthetic database to the new evidence directory, preserving the source and signing material. Start isolated loopback5246 from the new worktree/build; no writes to any prior database or origin. Retain the existing patient data in the copy; all new cases explicitly synthetic.
- [ ] Browser-check one-source automatic visibility, source drilldown, qualified chemistry/urine, mode/support/gas resolution, saved review/reload, culture/decision draft provenance and blood-fluid preservation. Use disposable fixture/API writes only; no external administration/order. Preserve screenshots and source/build/DB hashes.
- [ ] Dispatch independent whole-branch review on the exact base-to-final diff, design/plan, verification evidence and build manifest. Resolve important findings through one bounded fix wave and scoped rereview; rerun relevant/final checks when code changes warrant it.
- [ ] Rehash protected44 files, old source630/build12, main-layout8 and old combined database, proving original previews/data unchanged. Deliver candidate URL, reviewed commit, test results and remaining clinical limits; no M11 claim.

## Execution decisions

The user explicitly authorized this bounded implementation and independent review. Continue without another plan-approval interruption; the research and current instruction establish scope. A fresh builder checks this concrete design before code changes. One implementation task runs at a time, with independent task review and final whole-branch review. Root settles reversible implementation details in the ledger; destructive/security/external-publication actions remain outside authorization.
