# Pre-M11 Corrections Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation, followed by independent review.

**Goal:** Correct known bedside presentation/navigation defects before extending ClinRx to M11.
**Architecture:** Retain shared source owners, contracts and storage. Limit changes to frontend projection, clinical-setting defaults, wording and route synchronisation.
**Tech Stack:** Existing React, TypeScript, Vitest and Vite.
**Spec:** ../specs/2026-10-24-pre-m11-corrections-design.md

## Global Constraints
Preserve original/candidate preview assets and patient databases; no clinical activation, schema changes or mobile work. Preserve existing roadmap documentation edits and sources/.

## Review Focus
- Mixed-panel reports must not all follow one component's clinical category.
- Unknown clinical setting must reach evaluation unchanged.
- Empty or reconciled source sets must not imply complete exposure.
- URL/back navigation must preserve pending drafts, flags and unrelated query fields.
- Source values/units/identities remain unchanged beneath display corrections.

### Task 1: Overview and unit display
- [x] Add regressions in connectedOverview.test.tsx for legacy gases/SpO2/Hb placement, mixed-panel component routing, source preservation and dimensionless display.
- [x] Run and observe the regressions fail.
- [x] Correct PatientOverview.tsx area routing and RenalFluidEntryWorkspace.tsx unit display without modifying source records.
- [x] Verify focused overview and respiratory-context tests.

### Task 2: M10 default and subtotal language
- [x] Add transfusionWorkspace.test.tsx regressions for unknown clinical setting at render/evaluate and empty/reconciled/unresolved totals.
- [x] Run and observe failure, correct TransfusionWorkspace.tsx only, then run focused M10 tests.

### Task 3: Navigation and investigation associations
- [x] Add m7SharedWorkspace.test.tsx regressions for navigation URL, preserved query/hash, reload, legacy renal-key compatibility, invalid/disabled history destinations and blocked pending navigation.
- [x] Add catalog association assertions against the final roadmap in a focused test.
- [x] Observe failure; implement bounded route synchronisation and update presentation-only catalog module lists.
- [x] Verify the shared workspace and investigation regressions.

### Task 4: Verification and handoff
- [x] Run the full frontend suite with one worker; typecheck and immutable seven-flag build.
- [x] Freeze modified source and obtain independent read-only review; fix material findings with regressions.
- [ ] Browser-check the isolated corrected candidate without saves to preserved patient scope (coordinating reviewer owns this read-only check).
- [x] Compare source diff; record current assessment, test/build evidence and remaining M11 prerequisites. Preservation-hash comparison and final browser evidence are pending the coordinating reviewer’s isolated check.
