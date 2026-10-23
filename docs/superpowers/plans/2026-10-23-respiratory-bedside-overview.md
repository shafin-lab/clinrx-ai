# Respiratory Bedside Overview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the user-approved four-panel overview to the current respiratory workspace without replacing specialist sections or source workflows.

**Architecture:** A presentational overview consumes the existing scoped respiratory model and explicit selected sample. It links to existing tabs. No new patient feed, storage owner, clinical threshold or backend migration.

**Tech Stack:** Existing React, TypeScript, Vitest and CSS; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-23-m9-respiratory-abg-design.md`, interface section; user approved the linked outline and said to build while protecting prior work on 23 October 2026.

## Global Constraints

- Preserve existing respiratory specialist tabs, entry, source/history and local reviews.
- Preserve explicit sample selection, exact specimen/time placement and unconfirmed-evidence gates.
- Do not infer a current support setting, target, clinical assessment or treatment from source presence.
- Fluid balance/output stays in M8; use original shared records.
- No database writes/migration, original-preview replacement, dependency installation or production deployment.
- Use the current shared checkout because it includes concurrent uncommitted integration; save touched-file preimages and separate build outputs.
- Human approval covers native implementation here. Do not ask again for execution-method approval or change unrelated files.

## Review Focus

- Two support records: show both as selectable source evidence, never choose newest as current.
- Selected gas lost on refresh or wrong scope: summary cannot retain numeric values as current.
- Legacy source settings: display source assertions without independent alignment confirmation.
- Unconnected mechanics or absent review: show explicit gaps, never a normal/complete state.
- Mobile and keyboard users: cards fit the viewport, source links focus the selected destination, no hidden specialist functionality.

### Task 1: Scoped four-panel overview

**Files:** create `frontend/src/respiratory/RespiratoryBedsideOverview.tsx`; create `frontend/tests/respiratoryOverview.test.tsx`.

**Interfaces:** consume `ReturnType<typeof respiratoryModel>`, `current:boolean`, `selected?:RespiratorySample`, `onNavigate:(tab:RespiratoryTab)=>void`. Produce `RespiratoryBedsideOverview` with those props.

- [x] Write failing real-component tests: four headings; no auto-selected support/gas; explicit gas value and source-time context; unconfirmed state suppresses numeric summary; source-context versus confirmed alignment; existing-tab navigation; multiple support records.
- [x] Run `npm test -- --maxWorkers=1 tests/respiratoryOverview.test.tsx`; observe missing-module/behaviour failure before implementation.
- [x] Implement the four panels with labelled evidence counts/gaps and explicit selected gas; no independent arithmetic or clinical recommendation.
- [x] Rerun focused tests and confirm all expected behaviours.
- [x] Save a task-specific source snapshot; no shared-index commit while concurrent changes are present.

### Task 2: Integration, style and surgical clarity

**Files:** modify `RespiratoryWorkspace.tsx` and `respiratory.css`; extend overview/workspace tests.

**Interfaces:** use the existing `chooseTab` and `tabButtons` refs for overview actions; the selected sample remains owned by the workspace.

- [x] Write a failing integration test that the overview is visible and each action opens/focuses its existing section without deleting specialist tabs.
- [x] Add the overview above the tab list. Move existing evidence counts into a secondary disclosure, preserving their information.
- [x] Add responsive, accessible card styles following the current palette; retain visible uncertainty and specimen identity.
- [x] Add brief postoperative-context guidance distinguishing postoperative failure, prevention after planned extubation and deterioration after extubation, with linked evidence/source scope; no treatment controls.
- [x] Run overview/workspace/model/safety/integration tests and typecheck.
- [x] Save updated source snapshots and a diff against exact preimages.

### Task 3: Verify and demonstrate

**Files:** task output directory and `docs/m9-respiratory/` verification records.

- [x] Build ordinary and configured synthetic bundles into separate output folders.
- [x] Run the full frontend suite; investigate/report every observed failure. Repeat after new changes only as needed.
- [x] Check isolated synthetic previews with existing copied databases, source selection/tab navigation and actual1280px desktop/478px narrow layouts. Exact390px remains unverified; no original database writes.
- [x] Request final review of this delta; fix important findings before reporting completion.
- [x] Package design, source crosswalk, planned scenarios, actual verification and changed-file snapshots. Clearly distinguish planned cases from executed tests.

## Self-review

This plan implements the approved interface amendment and its safety boundaries.
Broader source-contract extensions, passive-mechanics clinical validation and
condition-specific treatment activation remain separately documented work. The
current source implementation is preserved and no new backend scope is introduced.

## Verification status after checkpoint a767c288

Tasks 1 and 2 are implemented with red/green regression evidence and passing focused tests/typecheck. Final read-only delta review found no important introduced issue. Task 3 is being verified on a frozen combined source manifest and immutable build. No claim of clinical readiness or comprehensive society compliance is made. Coordinator and independent reviewer roles follow the user's clarified division of work.

### User-requested optional findings amendment

The user requested chest examination (including air entry) and optional chest ultrasound, X-ray, CT/CTPA and MRI findings on 23 October 2026. This extends the existing bedside/imaging source categories, without a new store, interpretation engine or mandatory imaging requirement.

- [x] Add blank, optional examination and modality-specific report field templates.
- [x] Preserve original findings and correction history; adding fields does not overwrite existing values.
- [x] Add direct entry actions in the existing breathing and investigation sections.
- [x] Observe five failing real-component tests before implementation; verify six capture and navigation cases plus existing regressions.
- [x] Complete separate independent review, full frontend verification and browser demonstration of the optional-fields checkpoint.

Integration baseline build 061509 and its immutable source evidence remain separately preserved. Exact runtime/test identities and executed results belong in IMPLEMENTATION-VERIFICATION.json; planned clinical validation scenarios are not counted as tests.

Final verification: 1,156 frontend tests across52files and4,409 backend tests pass. Independent review and populated209-source workflow checks are clear. Final runtime build063355, source manifest70e103ed..., patchf7ccd87a.... Full records: docs/m9-respiratory/IMPLEMENTATION-VERIFICATION.json. M9 clinical validation remains in progress and M7-C stays gated.
