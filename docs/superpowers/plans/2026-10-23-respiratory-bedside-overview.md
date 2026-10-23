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

- [ ] Write failing real-component tests: four headings; no auto-selected support/gas; explicit gas value and source-time context; unconfirmed state suppresses numeric summary; source-context versus confirmed alignment; existing-tab navigation; multiple support records.
- [ ] Run `npm test -- --maxWorkers=1 tests/respiratoryOverview.test.tsx`; observe missing-module/behaviour failure before implementation.
- [ ] Implement the four panels with labelled evidence counts/gaps and explicit selected gas; no independent arithmetic or clinical recommendation.
- [ ] Rerun focused tests and confirm all expected behaviours.
- [ ] Save a task-specific source snapshot; no shared-index commit while concurrent changes are present.

### Task 2: Integration, style and surgical clarity

**Files:** modify `RespiratoryWorkspace.tsx` and `respiratory.css`; extend overview/workspace tests.

**Interfaces:** use the existing `chooseTab` and `tabButtons` refs for overview actions; the selected sample remains owned by the workspace.

- [ ] Write a failing integration test that the overview is visible and each action opens/focuses its existing section without deleting specialist tabs.
- [ ] Add the overview above the tab list. Move existing evidence counts into a secondary disclosure, preserving their information.
- [ ] Add responsive, accessible card styles following the current palette; retain visible uncertainty and specimen identity.
- [ ] Add brief postoperative-context guidance distinguishing postoperative failure, prevention after planned extubation and deterioration after extubation, with linked evidence/source scope; no treatment controls.
- [ ] Run overview/workspace/model/safety/integration tests and typecheck.
- [ ] Save updated source snapshots and a diff against exact preimages.

### Task 3: Verify and demonstrate

**Files:** task output directory and `docs/m9-respiratory/` verification records.

- [ ] Build ordinary and configured synthetic bundles into separate output folders.
- [ ] Run the full frontend suite; investigate/report every observed failure. Repeat after new changes only as needed.
- [ ] Create an isolated fixture preview of the real component, with synthetic labelling and no patient-database connection. Check desktop/mobile, selection and tab navigation.
- [ ] Request final review of this delta; fix important findings before reporting completion.
- [ ] Package design, source crosswalk, planned scenarios, actual verification and changed-file snapshots. Clearly distinguish planned cases from executed tests.

## Self-review

This plan implements the approved interface amendment and its safety boundaries.
Broader source-contract extensions, passive-mechanics clinical validation and
condition-specific treatment activation remain separately documented work. The
current source implementation is preserved and no new backend scope is introduced.
