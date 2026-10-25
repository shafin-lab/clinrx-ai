> Historical combined-source plan, superseded by the NCDC-only scope in `../specs/2026-10-25-infection-library-design.md` on 25 October 2026. Prior checkpoint and verification remain in Git history.

# Infection Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace the active medicine-group reference entry point with the approved NCDC-first infection library, preserving all prior work and patient data.

**Architecture:** A separate static source-backed catalogue and pure lookup model feed a read-only React library. The existing reference export mounts the new library; old reference UI/data remain retained but unmounted. No backend schema or patient-write API changes.

**Tech Stack:** React, TypeScript, Vitest, Python source extraction, existing loopback preview gateway.

**Spec:** `docs/superpowers/specs/2026-10-25-infection-library-design.md`

## Global Constraints
- NCDC takes precedence over JIPMER for overlapping clinical contexts.
- No CRRT section, antibiotic monographs or automatic renal adjustment.
- No patient writes, original-preview replacement, synced-source edits, or edits to other worktrees.
- All newly transcribed guidance remains unreviewed, non-executable and not local policy.
- Do not infer missing doses, routes, durations, age/weight conditions or formulation.

## Review Focus
- A similar infection with a different age, severity, acquisition setting or organism must not inherit the wrong regimen.
- Source pagination, multiline tables and merged cells must not attach a dose to the wrong case.
- Search/group changes must clear stale selections and never leave a previous infection's dose visible.
- Missing or conditional guidance must remain explicit, without inventing a fixed prescription.
- Browsing with a stale patient snapshot or unsubmitted form must not trigger a write or lose the original checkpoint.

## Shared data interface
`frontend/src/infectionLibrary/data/infection-guidance.json`: `{version, sources:[{id,name,version,url,sha256}], groups:[{id,name}], infections:[{id,groupId,name,aliases:string[],cases:[{id,label,sourceId,locator,pdfPages:number[],regimens:[{id,label,instructions:string,duration:string|null,gaps:string[]}],notes:string[],gaps:string[]}]}]}`. Source IDs are `ncdc` and `jipmer`. Cases own source provenance. Instructions are source factual treatment fields, never an assembled cross-source dose. Explicit alternatives are selectable where unambiguous; otherwise a gap is retained. Data-level boolean fields `executable:false`, `clinical_use_eligible:false`, `review_status:'unreviewed'` apply.

### Task 1: Source catalogue and precedence
**Files:** create `frontend/src/infectionLibrary/data/infection-guidance.json`, `tools/build_infection_guidance.py`, `docs/antibiotics/INFECTION-SOURCE-MAPPING.md`, `frontend/tests/infectionCatalogue.test.ts`.
- [x] Write failing source coverage/precedence tests, including CAP, source gaps, JIPMER renal/perinephric abscess additions, same-context precedence, all 19 groups, unique IDs and valid pages/hashes.
- [x] Run tests and record RED; extract/curate all NCDC named infection sections and map JIPMER system-specific contexts without duplicated overlap.
- [x] Verify sampled numerical/conditional fields against original source tables. Record held or missing fields explicitly; run tests GREEN.
- [x] Commit source catalogue, generator, crosswalk and tests.

### Task 2: Read-only integrated UI
**Files:** create `frontend/src/infectionLibrary/InfectionLibrary.tsx`, `infectionLibrary.css`, `catalogue.ts`; preserve old `AntibioticReferences.tsx` as `LegacyAntibioticReferences.tsx`; replace active export; add `frontend/tests/infectionLibrary.test.tsx`, update legacy test import.
- [x] Write failing tests for all groups, real search, one source/case/regimen selection, JIPMER additions, empty states, no CRRT/medicine catalogue UI, no fetch/storage/prescription side effects and selection invalidation.
- [x] Run tests RED; implement from the shared data interface and existing page styling.
- [x] Run focused and full frontend tests, typecheck and build; preserve legacy content and other workspaces.
- [x] Commit implementation and tests.

### Task 3: Independent checkpoint review and new preview
**Files:** add launch instructions and verification/preservation record under `docs/antibiotics/` and ignored `review-evidence/infection-library/`.
- [x] Freeze the checkpoint and request a fresh whole-change review of source matching and UI behavior.
- [x] Correct material findings with reproducing tests and run relevant checks.
- [x] Back up the current synthetic SQLite database into this candidate's runtime directory; launch a new loopback origin using the reviewed frontend.
- [x] Verify browser group→infection→context→regimen workflow, JIPMER additions, returning to culture/patient/overview and reload; make no patient saves.
- [x] Recheck original build/database/sources hashes and SQLite integrity. Record exact coverage, tests, limitations, candidate URL and commit.

Verification and qualified content coverage: `docs/antibiotics/INFECTION-LIBRARY-HANDOFF.md`. The original preview remains unchanged; this is an independently reviewed reference preview, not completed clinical content validation.
