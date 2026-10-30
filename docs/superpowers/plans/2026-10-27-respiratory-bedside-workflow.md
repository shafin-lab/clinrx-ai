# Respiratory bedside workflow implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** A simple respiratory bedside interface backed by a durable shared ABG and respiratory-support history.

**Architecture:** Retain the append-only respiratory endpoint and shared catalog. Add optional typed episode metadata with legacy serialization preservation, a cutoff-bounded support resolver, and focused bedside components; reuse the original source entry/review machinery and specialist content.

**Tech Stack:** Existing React/TypeScript, Vitest, Python/Pydantic, SQLite and FastAPI gateway.

**Spec:** `docs/superpowers/specs/2026-10-27-respiratory-bedside-workflow.md` (approved conversation/demo, recorded here).

## Global Constraints

- Preserve all existing work and patient records; `sources/` is read-only.
- Existing preview builds and databases on 5246/5247/5249/5251 stay untouched.
- No guessed FiO2, missing-as-normal findings, duplicate patient stores, or merged specimens.
- Clinical formulas and execution gates stay in their established owners.
- Mobile verification is deferred. No society endorsement or clinical-readiness claim.

## Review Focus

- Corrected or withdrawn support must not revive an older episode as current.
- Unknown-time support, same-instant disagreements and overlapping explicit episodes must withhold resolution.
- A late-entered source cannot leak past the historical availability cutoff.
- Changing a support device/mode must not submit hidden settings from the previous selection.
- Pending source retries preserve exact bytes; corrected legacy source payloads retain units and methods.

### Task 1: Durable support history and sample-time resolution

**Files:** `backend/app/models/clinical/respiratory.py`, generated `frontend/src/api/rf2Schemas.json`, `frontend/src/respiratory/respiratoryTypes.ts`, new `supportModel.ts`, `respiratoryEvaluation.ts`; tests `tests/test_respiratory_contract.py`, `tests/test_respiratory_gateway.py`, `frontend/tests/respiratorySupport.test.ts`.

**Interfaces:** Produces optional `context.support_episode` with typed device and nullable exact end time, `respiratorySupportTimeline(catalog, requested)` and `supportAtTime(catalog, at)` returning original evidence, resolution status and reasons. Existing sources without episode metadata remain point observations.

- [x] Write contract tests proving legacy canonical payload equality, episode round-trip, invalid ends/category rejection, and gateway reload/history/idempotence.
- [x] Write model tests with literal times/values for room air → nasal → HFNC → intubation → invasive ventilation, earlier support before the review window, same-time conflict, withdrawal, point interruption, future availability, explicit ending/overlap and cross-patient rejection.
- [x] Run tests RED, then implement optional metadata, source-preserving timeline/resolution, and generated schema. Preserve existing explicit linked simultaneous evaluation; permit automatic episode-derived FiO2 only when scope/status/quality/unit/prerequisites are satisfied and direct sample values do not conflict.
- [x] Run backend respiratory tests and frontend support/evaluation/model/transport tests GREEN; commit.

### Task 2: Simple bedside report, support entry and shared views

**Files:** new focused components under `frontend/src/respiratory/`, existing `RespiratoryWorkspace.tsx`, `RespiratoryEntry.tsx`, `respiratoryCatalog.ts`, `respiratory.css`, `frontend/src/demo/PatientOverview.tsx`; focused component/integration tests.

**Interfaces:** Consumes Task 1's evidence timeline/resolver; produces four primary respiratory views, one source-preserving ABG table and device/mode-specific routine entry backed by `importRespiratory`. Overview consumes the same original support records.

- [x] Add failing tests for complete ABG parameters in one specimen report, latest automatic selection, previous values, correct venous labels, missing-vs-zero values and unit preservation.
- [x] Add failing entry tests for room air, nasal/mask, HFNC flow + FiO2, NIV/invasive mode fields, hidden-setting removal, source corrections and exact pending retries.
- [x] Implement routine fields and collapsed advanced metadata using the existing save/review contract; no prefilled patient clinical values. Keep specialist/care/source features accessible from the simpler screen.
- [x] Add integration tests for one save appearing automatically in respiratory history and patient overview after refresh/remount, without a second write; stale catalog disables saves.
- [x] Run focused frontend tests and typecheck GREEN; commit.

### Task 3: Verify and present a preserved-data preview

**Files:** `review-evidence/respiratory-workflow-20261027/` scripts/evidence and `docs/consolidation/PLAN.md` handoff.

**Interfaces:** Consumes the implemented checkpoint. Produces a build and new local preview backed only by a copied database, plus an independent frozen-checkpoint review and full verification record.

- [x] Run frontend suite with four workers, backend maintained suite with repository/test import paths, typecheck, build and whitespace checks. Expected: all maintained tests pass; report actual warnings/skips.
- [x] Commit checkpoint and request independent read-only review against spec, plan and Review Focus. Resolve material findings with RED→GREEN regressions.
- [x] On a separate database copy, verify populated ABG/support progression, correction, idempotence, historical cutoff, reload persistence, shared overview, imaging/PFT access and unchanged antibiotics/M7/M8 navigation. Inspect desktop browser and capture evidence; defer mobile.
- [x] Verify original database hashes/integrity match baseline, preserve earlier builds and leave existing servers untouched. Start the updated candidate on an unused local port and show it to the user; record commit, launch and remaining limitations.
