# ClinRx GitHub Consolidation Implementation Plan

> For agentic workers: execute the bounded integration tasks, then independently review the frozen combined checkpoint before merge.

**Goal:** Push and merge all completed main ClinRx workflow work into shafin-lab/clinrx-ai main while preserving previews and patient data.

**Architecture:** Keep the existing multi-system workspace and source-owned clinical contracts. Save the antibiotic integration, reconcile GitHub main ancestry, recover only the incremental Echo/BP/PFT/ABG presentation changes, and validate one combined source checkpoint. Do not overwrite newer respiratory or saved-review behavior with an older candidate.

**Tech Stack:** React/TypeScript/Vitest/Vite; Python/FastAPI/pytest; existing GitHub Actions.

**Spec:** User authorisation in this chat, existing ANTIBIOTIC-PROFILES-INTEGRATION.md, recovered eight-file cardiorespiratory candidate at f6a176a baseline.

## Global constraints
- Preserve sources/, databases, browser review stores and all existing served builds.
- Upload only reviewed repository source/reference material and synthetic test fixtures; exclude local databases, keys, dependencies and runtime evidence archives.
- Preserve NCDC guidance, all 94 draft antibiotic profiles, saved review invalidation, ventilator modes, support progression and source/cutoff integrity.
- Do not activate clinical execution or deploy a live clinical app. Mobile checks deferred.
- User has explicitly authorised GitHub push and merge; no additional plan/finish confirmation is needed.

## Review focus
- Older candidate content must not revert newer saved-review and respiratory workflow behavior.
- Blood-pressure pairing must respect exact time, acquisition context, units and ambiguous duplicates.
- ABG report and PFT views must retain source evidence and not mix samples or fabricate values.
- Public Git history must exclude credentials and patient/runtime databases.
- GitHub main must contain the exact independently reviewed, passing combined source, not merely a separate branch or reference tags.

### Task 1: Preserve and map source ownership
- [x] Commit approved antibiotic integration as 80647a2; exclude node_modules.
- [x] Fetch GitHub main, verify current head and merge equivalent earlier pre-M11 corrections without changing the newer source tree.
- [x] Preserve all eight surviving candidate files, baseline and checksums in ignored local evidence.

### Task 2: Reconcile independent clinical presentation domains
- [x] Hemodynamics: resolve M7BedsideReview.tsx and hemodynamicBedside.test.tsx conflicts, retaining current persistence/guards and new exact-time BP/echo layout. bedside.css applied cleanly.
- [x] Respiratory: resolve RespiratoryWorkspace.tsx, RespiratoryEntry.tsx, respiratoryCatalog.ts, respiratory.css and respiratoryWorkspace.test.tsx; retain current simplified bedside report, support timeline, modes and persistent sample selection. Incorporate applicable PFT/ABG display increments with tests.
- [x] Run targeted tests: M7 66/66, respiratory 108/108. All eight recovered files already have superseding implementations in HEAD; conflict resolution retains HEAD byte-for-byte. No clinical presentation rewrite is needed.

### Task 3: Verify one combined checkpoint
- [ ] Merge gate: full backend and GitHub checks must pass. Local full frontend, typecheck, schema head m10_0011 and both builds passed. Backend full run underway when this plan was committed; final exact-head results belong in the PR validation record.
- [x] Independently reviewed the combined changes. Corrected exact support-end timestamp normalization and same-value renal source renewal with red/green regressions; re-review closed both findings. Full frontend 1,754 passed / three skipped, typecheck and default/seven-flag builds passed. Parent/inspector test readiness now waits on actual UI conditions.
- [x] Audited 345 changed files and new history: no runtime/database/key/dependency files or credential-pattern hits; four patient DB hashes unchanged.

### Task 4: GitHub integration
- [ ] Push consolidation branch and create/attach PR against main with exact validation evidence and limits.
- [ ] Wait for required GitHub checks and address failures.
- [ ] Merge the reviewed head without bypassing protections; verify remote main contains it.
- [ ] Record final commit/PR, preserved preview and remaining scope in handoff documentation.

## Publication record

This checklist records the pre-publication checkpoint. Final remote push, CI and merge status is maintained in the consolidation pull request against shafin-lab/clinrx-ai main. Publishing the branch does not activate clinical execution or replace a patient preview.
