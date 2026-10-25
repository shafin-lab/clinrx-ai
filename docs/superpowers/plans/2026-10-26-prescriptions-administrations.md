# Prescriptions and administrations Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for implementation and an independent final code review.

**Goal:** Implement the approved integrated prescriptions page with automatic recorded-input CrCl, individual renal dose review and actual administration history.

**Architecture:** Read the canonical patient bundle. Derive a typed course/history view and automatic renal input view without new laboratory or medication stores. Persist explicitly reviewed missing patient context as a strictly versioned shared RF2 note; preserve existing medication commands and exact recovery.

**Tech Stack:** React/TypeScript, Vitest, existing Python/FastAPI/SQLite source commands.

**Spec:** `docs/superpowers/specs/2026-10-26-prescriptions-administrations-design.md` (records the user-approved demo and implementation constraints).

## Global Constraints

- Preserve original preview, all prior builds, patient databases and read-only `sources/`.
- NCDC and supplementary reference content remain unchanged; no runtime inheritance from the reference JSON.
- No inferred patient demographics, renal stability, administrations, schedules or treatment indication.
- No routine CrCl-based suggestion for dialysis, evolving AKI, stale/missing/conflicting sources or unsupported drug context.
- Suggestion acceptance opens a reviewed draft/correction only; never silently saves or administers.
- Mobile checks deferred by user.

## Review Focus

- A newer unusable, future or corrected result must not silently allow an older unsafe dose context.
- Concurrent context/source changes and pending commands must not unlock stale suggestions or lose recovery bytes.
- Same drug in separate courses or unlinked MAR records must not be merged by name.
- Correcting a prescription must preserve actual prior administered doses and exact linked order revision.
- Low but stable renal function must not be labeled normal; missing demographics and kidney support must stay unknown.

### Task 1: Recorded renal input and medication course models

Files: create `frontend/src/antibioticWorkflow/automaticRenalModel.ts`, `therapyModel.ts`; test `frontend/tests/automaticRenalModel.test.ts`, `therapyModel.test.ts`.

- [x] Add RED tests for latest eligible source selection, units, cutoff/availability, ties, corrected/withdrawn sources, age/coefficient context, creatinine rise and freshness.
- [x] Implement pure source-selection/context arithmetic with exact provenance and stable signatures.
- [x] Add RED tests for explicit order grouping, independent courses, unlinked records, duplicate source identity, correction chains and all actual non-delivery statuses.
- [x] Implement course/history view without synthetic administrations or schedules; run focused model tests.

### Task 2: Compact shared context, per-medicine suggestions and preserved commands

Files: create `AutomaticRenalSummary.tsx`, `PatientDoseContext.tsx`, `PrescriptionChart.tsx`, `MedicationDoseReview.tsx`; modify `AntibioticWorkspace.tsx`, `AntibioticRecordEditor.tsx`, `antibioticWorkflow.css`; add workflow tests.

- [x] Write and observe failing clinician-flow tests: automatic refresh, collapsed inputs, medicine details/history, missing context, suggestion-to-correction with old MAR intact, no-write rendering and multiple medicines.
- [x] Build strict versioned context note parsing/saving with repository-scoped exact-request recovery, review and explicit retry; no auto-append.
- [x] Compose full-width chart and one details panel; remove the large always-visible advisor from this page, retaining its legacy implementation.
- [x] Preserve original correction metadata, add explicit new-source suggestion corrections with retained old candidate context and stale-evidence guards.

### Task 3: Source profile and transport boundaries

Files: modify `renalDoseModel.ts`, `backend/app/api/schemas/antibiotic_chart.py`, `backend/app/services/antibiotic_chart_service.py`, generated `antibioticSchemas.json`; frontend/backend profile and source tests.

- [x] Verify current primary dosing references and preserve exact profile applicability.
- [x] Test and add explicit renal-review context pin and laboratory-component pin support, preserving legacy canonical bytes and rejecting invalid component references.
- [x] Test anidulafungin maintenance only, unsupported teicoplanin, boundary gaps, dialysis and AKI holds.

### Task 4: Review, verify and publish

- [x] Full frontend suite, typecheck, production build and applicable backend suite; record any unrelated failures accurately.
- [x] Independent review of a fixed commit, correct material findings and run their regressions.
- [x] Desktop checks against an isolated populated verification database copy; confirm actual given/held/not-given history and correction behavior without real database writes.
- [x] Preserve old candidate assets, publish the updated preview and compare database hashes/integrity and reference/source manifests.

## Execution ledger

Baseline: existing isolated branch `codex/infection-library-20261025`; no tracked modifications. Current preview build archived. Both patient databases SHA256 `cb3d6abdad8b3f91fd32a1eeca7890917e8cfb08c34f5fbcceae0283a22c0b14`, integrity ok, 209 fact revisions each.

Implementation checkpoint: 104 focused frontend tests passed, including the original antibiotic recovery/correction suites and the new source-selection, history, context recovery and prescription correction flows. Sixteen antibiotic backend tests passed, including byte-identical legacy requests and explicit new-review corrections with original history retained. Initial independent model review identified weight-pin, historical-trend, unknown-time and presentation gaps; their regressions were observed RED and passed after correction. Full suites and desktop verification are in progress.

The shared context uses the existing RF2 note carrier with a strict versioned findings shape and exact source pins. No migration or duplicate patient/laboratory store was introduced. The original candidate-dose context remains immutable on ordinary corrections; an explicit `dose_review_amendment` appends a new context with the authenticated predecessor retained in source history.


Final verification checkpoint `6d0e383` (2026-10-26):

- Full frontend suite: **1,620 passed, 3 skipped**. Final TypeScript check and full-feature production build passed; existing large-chunk warning remains. An earlier shared-workspace integration test clicked the new Add button while evidence was still loading; it now waits for the enabled action and continues to verify the navigation/source guard. Two earlier invocation-path failures were resolved by running from the frontend directory. Final logs are in `review-evidence/prescriptions-20261026/`.
- Full backend suite at implementation checkpoint: **4,537 passed**. After the bounded prior-day-history addition, all **17 antibiotic backend tests passed**, including prior-day inclusion, exclusion of future events and exclusion of records ingested after the authenticated cutoff. The entire backend suite was not repeated after that read-only endpoint addition.
- Independent review of `a1e171b` identified three remaining renal-source issues: changed/falling creatinine reusing an older stability review, unresolved observation identity, and unknown-time weight fallback. Corrected with regressions; withdrawn weight and cancelled-prescription display also withhold suggestions. Actual owned RF2 synthetic context carriers deliberately use unresolved synthetic binding; they remain scoped to the explicit local synthetic target, while observations and laboratory reports require verified binding. This distinction was independently reviewed.
- Desktop verification used only `verification-desktop.sqlite3`, copied from the candidate. Synthetic stable creatinine, measured weight, explicit demographics and renal context produced **25.0 mL/min**. The meropenem candidate appeared beside its order after indication/product/phase/infusion review. Accepting it opened an explicit correction; validation and save appended a new prescription revision. After reload the prescription was 500 mg every 12 hours, while the earlier actual **1 g** dose and held/missed records retained their original values and reasons. A separate multi-day course demonstrated the earlier-day administration appearing automatically when details opened, without a reuse action or duplicate entry.
- No real or preserved-preview patient record was saved. Both preserved databases still have SHA256 `cb3d6abdad8b3f91fd32a1eeca7890917e8cfb08c34f5fbcceae0283a22c0b14` and integrity `ok`. Prior builds/hashed assets and signing material are retained. NCDC and supplementary library assets remain byte-identical; synced `sources/` remain untouched.

Practical limits: the preserved historical patient lacks DOB/equation coefficient and includes deliberately unusable creatinine evidence, so the live patient page correctly withholds a calculation rather than inserting demo values. New context is recorded at its actual save time; it is not silently backdated into an earlier historical review. Source-limited adult candidates cover seven existing renal profiles and anidulafungin maintenance; unsupported drugs (including teicoplanin) and AKI/dialysis/ambiguous contexts show review requirements. This remains a synthetic, non-executing preview, not a clinically validated prescribing service. Mobile checks are deferred at the user's request.

Final narrow independent review found one P2: a newly loaded prior-day row attempted revision-history retrieval using the original narrow state. Workspace now retains the authenticated expanded state, selects the appropriate state by exact source reference, and invalidates prior revision-history requests when changing course. The regression was observed failing with the old dispatch and is included in the final frontend run.
