# Respiratory Quick Entry Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. Native execution follows the user's established method; independent checkpoint review stays with Superpower Review.

**Goal:** Implement the user's explicit quick-choice/free-text/Advanced layout in the existing findings form.
**Architecture:** Presentation-only change to existing typed rows and validation; no second store.
**Tech Stack:** React, TypeScript, existing CSS and Vitest.
**Spec:** docs/superpowers/specs/2026-10-23-respiratory-quick-entry-design.md

## Global Constraints
Preserve existing uncommitted work and original source bytes. No source/database/schema/execution changes. Use the current shared candidate because its verified uncommitted respiratory integration is absent from HEAD-only worktrees; save preimages and immutable build evidence. No blanket commit or merge.

## Review Focus
- Blank findings stay blank; no preselected normality.
- Editing quick choices must be explicit; Other and free text preserve source wording.
- Hidden Advanced controls retain values, types, units, coding and quality; opening a disclosure never changes a source.
- Required source reference remains enforced and discoverable.
- Numeric ABG/mechanics workflows and exact pending retry/corrections remain unchanged.

### Task1: Quick findings and Advanced layout
- [x] Write and observe failing real-component tests for quick selection/free text, hidden-but-retained Advanced controls, correction preservation, missing-source guidance and unchanged ABG controls.
- [x] Add field-specific choice data and a small reusable editable finding input; modify RespiratoryEntry/CSS only as needed.
- [x] Run focused findings/workspace/transport tests and typecheck; fix failures without weakening assertions.

### Task2: Independent review and demonstration
- [x] Freeze source/patch/new files, run the complete frontend suite and synthetic/default builds.
- [x] Obtain independent read-only review of that identified source and fix consequential findings with regressions.
- [x] Browser-check quick choices, custom wording, Advanced and metadata guard on an isolated preview without patient writes; preserve screenshot.
- [x] Record final verification, source identity and remaining clinical gates; coordinate preview promotion after checks.

## Verification checkpoint
- Frozen source: `review-evidence/m9-respiratory/quick-entry-freeze-20261023T065534Z` (404 manifest entries).
- Focused respiratory coverage: 63 tests / 7 files passed; typecheck and synthetic/default builds passed.
- Independent read-only review cleared this exact checkpoint; source semantics and guards preserved.
- No-save browser check passed; screenshots and browser-check.json stored with checkpoint.
- First full run: 1,161 passed, 2 failed in existing screen-arrival queries (53 files; exit1). Concurrent M10 test load observed. Failure log preserved; diagnosis uses unchanged tests and budgets. Promotion remains withheld pending a clean current-source full run.

- Final full run on unchanged frozen source: 1,163 tests / 53 files passed, exit0, 200.02s. Quiet diagnostic33/33 and cardiac singlecase passed. All404 hashes matched after verification. No assertion, timeout or runtime changes were needed.

- Coordinator promoted reviewed build065536 to candidate5241. Final preservation audit confirms all three database hashes unchanged (171/171/209 facts), originals/revision/execution tables intact. Original5238 and earlier063355 build retained.
