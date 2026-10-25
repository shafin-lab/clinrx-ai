# Supplementary infection evidence implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline; request one independent review of the finished checkpoint.

**Goal:** Add the approved expandable supplement without changing NCDC or patient data.

**Architecture:** A typed, static source registry and distinct evidence entries resolve by exact NCDC infection/row IDs. A separate read-only component follows the unchanged NCDC panels and source details.

**Tech Stack:** Existing React/TypeScript, native details/summary, Vitest/Testing Library; no dependencies.

**Spec:** `docs/superpowers/specs/2026-10-25-supplementary-infection-evidence.md`

## Global constraints

2023–2026 substantive source versions only; source-specific population limits; no mixed-source regimen; NCDC bytes unchanged; no patient/store/network writes; no JIPMER/CRRT/monographs; preserve original preview and rollback build.

## Review focus

- Row-specific teicoplanin/HSV/sepsis material must disappear for a different clinical situation.
- Repeated bindings must not repeat a card or source; original NCDC text stays outside the supplement.
- No supplementary section for unrelated, unavailable or unmatched infections.
- Changing infection or situation closes expanded material and removes stale content.
- Source dates, external doses, limits and URLs must be verified; context-only material must not masquerade as a full regimen.

### Task 1: Catalogue, expandable view and preservation

**Files:** Create `frontend/src/infectionLibrary/supplementaryCatalogue.ts`, `SupplementaryEvidence.tsx`, `frontend/tests/supplementaryEvidence.test.tsx`, `supplementaryCatalogue.test.ts`; modify `CompleteNcdcLibrary.tsx` and scoped styles; add handoff evidence. Do not edit NCDC data or assets.

**Interfaces:** `supplementaryFor(infectionId: string, rowId?: string): SupplementaryEntry[]`; `SupplementaryEvidence({infectionId, rowId})`. Sources and entries have stable IDs; each entry owns its source-specific schedule or context and limits.

- [x] Write tests for the review-focus cases, actual approved teicoplanin schedule and source registry/binding uniqueness. Observe expected failure before implementation.
- [x] Implement static reviewed references and native expandable component; add beneath existing source panel. Keep source text unchanged and update only the introductory description to distinguish primary NCDC from optional external reading.
- [x] Run focused tests, full frontend suite with four workers, typecheck/build, whitespace and NCDC/database/original-preview manifest comparisons. Final: 1,562 passing tests, three existing skips; typecheck/build passed.
- [x] Freeze a local checkpoint and request independent code/content review. No material findings; subsequent desktop CSS finding covered RED–GREEN with the actual global stylesheet.
- [x] Publish the versioned candidate build at 5247 with rollback preserved. Browser-checked disclosure, context clearing, unrelated infections, source links, navigation and reload without entering/saving patient data. Final preservation record and screenshot are in the handoff.

User's explicit implementation instruction supplies execution authorization; no additional design/plan approval requested.
