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

- [ ] Add RED tests for latest eligible source selection, units, cutoff/availability, ties, corrected/withdrawn sources, age/coefficient context, creatinine rise and freshness.
- [ ] Implement pure source-selection/context arithmetic with exact provenance and stable signatures.
- [ ] Add RED tests for explicit order grouping, independent courses, unlinked records, duplicate source identity, correction chains and all actual non-delivery statuses.
- [ ] Implement course/history view without synthetic administrations or schedules; run focused model tests.

### Task 2: Compact shared context, per-medicine suggestions and preserved commands

Files: create `AutomaticRenalSummary.tsx`, `PatientDoseContext.tsx`, `PrescriptionChart.tsx`, `MedicationDoseReview.tsx`; modify `AntibioticWorkspace.tsx`, `AntibioticRecordEditor.tsx`, `antibioticWorkflow.css`; add workflow tests.

- [ ] Write and observe failing clinician-flow tests: automatic refresh, collapsed inputs, medicine details/history, missing context, suggestion-to-correction with old MAR intact, no-write rendering and multiple medicines.
- [ ] Build strict versioned context note parsing/saving with repository-scoped exact-request recovery, review and explicit retry; no auto-append.
- [ ] Compose full-width chart and one details panel; remove the large always-visible advisor from this page, retaining its legacy implementation.
- [ ] Preserve original correction metadata, add explicit new-source suggestion corrections with retained old candidate context and stale-evidence guards.

### Task 3: Source profile and transport boundaries

Files: modify `renalDoseModel.ts`, `backend/app/api/schemas/antibiotic_chart.py`, `backend/app/services/antibiotic_chart_service.py`, generated `antibioticSchemas.json`; frontend/backend profile and source tests.

- [ ] Verify current primary dosing references and preserve exact profile applicability.
- [ ] Test and add explicit renal-review context pin and laboratory-component pin support, preserving legacy canonical bytes and rejecting invalid component references.
- [ ] Test anidulafungin maintenance only, unsupported teicoplanin, boundary gaps, dialysis and AKI holds.

### Task 4: Review, verify and publish

- [ ] Full frontend suite, typecheck, production build and applicable backend suite; record any unrelated failures accurately.
- [ ] Independent review of a fixed commit, correct material findings and run their regressions.
- [ ] Desktop checks against an isolated populated verification database copy; confirm actual given/held/not-given history and correction behavior without real database writes.
- [ ] Preserve old candidate assets, publish the updated preview and compare database hashes/integrity and reference/source manifests.

## Execution ledger

Baseline: existing isolated branch `codex/infection-library-20261025`; no tracked modifications. Current preview build archived. Both patient databases SHA256 `cb3d6abdad8b3f91fd32a1eeca7890917e8cfb08c34f5fbcceae0283a22c0b14`, integrity ok, 209 fact revisions each.

Implementation checkpoint: 104 focused frontend tests passed, including the original antibiotic recovery/correction suites and the new source-selection, history, context recovery and prescription correction flows. Sixteen antibiotic backend tests passed, including byte-identical legacy requests and explicit new-review corrections with original history retained. Initial independent model review identified weight-pin, historical-trend, unknown-time and presentation gaps; their regressions were observed RED and passed after correction. Full suites and desktop verification are in progress.

The shared context uses the existing RF2 note carrier with a strict versioned findings shape and exact source pins. No migration or duplicate patient/laboratory store was introduced. The original candidate-dose context remains immutable on ordinary corrections; an explicit `dose_review_amendment` appends a new context with the authenticated predecessor retained in source history.
