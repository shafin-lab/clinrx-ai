# Saved Dose Reviews Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline with test-driven-development and one fixed-checkpoint independent review.

**Goal:** Restore unchanged per-medicine suggestions after reload and focus review on relevant changes.
**Architecture:** Strict local review log, pure dependency evaluation, small review hook/UI integrated into the existing chart. Recompute current candidates; preserve all existing source and medication commands.
**Tech Stack:** React/TypeScript, browser Web Locks/localStorage, existing typed snapshot/history APIs.
**Spec:** docs/superpowers/specs/2026-10-26-saved-dose-reviews-design.md

## Constraints
- No original patient-store or synced source writes. Preserve main/demo assets and storage keys.
- Browser-local synthetic review; no new clinical storage promise, no cached-dose authority.
- Current source eligibility and explicit prescription save gates remain in force.
- No migration or new clinical dose profiles; mobile checks deferred.

## Tasks
- [x] RED dependency/log tests: reload, separate scopes/courses, unrelated facts, relevant values/product/treatment/culture/profile/history changes, lower cutoff/earlier view, strict malformed storage and queued/concurrent saves.
- [x] Implement pure dependency groups and strict bounded append-only persistence (`savedDoseReviews.ts`).
- [x] RED workflow tests for saved restoration, specific changed-input review, compatible check preservation, history failure, no silent order writes.
- [x] Add a chart review hook (`useSavedDoseReviews.ts`), explicit save/reviewer/receipt UI, and bounded history hydration for saved reviews in `AntibioticWorkspace.tsx`.
- [x] Run focused and complete frontend tests, typecheck/build. Commit fixed checkpoint and obtain independent review; fix material findings.
- [x] Verify save/reload/change/irrelevant-update in an isolated populated copy, preserve hashes of existing stores, publish assets with rollback available, show updated preview.

## Review focus
Stale approval at lock acquisition; hidden cross-tab changes; persisted dose bypassing recomputation; source scope/time rollback; history hydration changing dependency sets; missing clinical evidence; updates to unrelated medicines; preserving original orders/MAR and malformed bytes.

## Ledger
Baseline `fbc1c72`; tracked tree clean. Current main and populated-demo builds archived; database hashes recorded before work. Inline implementation, one independent review at a fixed commit. Browser-local storage is the bounded preview implementation; shared authenticated audit remains future scope.


## Completed checkpoint and verification
Implementation `dc18729`, independent review corrections `9d82b83`. Read-only review found two P2 edges: reject a queued save if the selected review end moves earlier, and normalize exact decimal scale for otherwise compatible maintenance amounts. Both corrected and regression tested; reviewer confirmed no remaining material findings.

Final frontend suite: **1,638 passed, 3 skipped**, 77 passing files / 2 skipped. Focused persistence/workflow tests:24 passed. Typecheck, full-feature production build and diff whitespace check passed. Existing large-chunk warning remains. No backend source or clinical dose profile changed.

Browser verification on isolated port5250: three medicine receipts saved and restored after reload; unrelated source/cutoff update preserved all three; changed creatinine3→2.5mg/dL and separately refreshed shared context recalculated CrCl25→30, withheld old approvals, retained compatible product/rationale/phase/infusion checks and offered Save updated dose review. Missing history, malformed storage, quota failure, lower cutoff, queued/concurrent writes and scope separation covered by regressions. Browser saves left the isolated copy's full logical SQLite dump identical to the original fictional demo (SQLite backup has different physical header bytes).

Published additive hashed assets and atomic entry HTML to existing5247 and5249. Previous builds remain in review-evidence/saved-dose-reviews-20261026/previous-main-build and previous-demo-build; old assets retained. Original5246 untouched. Populated5249 remains CrCl25 with original prescriptions and MAR, and now has explicit browser-local Fictional demo reviewer receipts for all three medicines; reload restored all three without repeated form checks. Its fictional banner/CSP-compatible CSS preserved. All three existing SQLite databases retain baseline SHA256 and integrity ok (209/28/209 revisions). No prescription, administration or shared patient-context record saved to existing stores. Temporary5250 verification server stopped. Mobile deferred.

Evidence: review-evidence/saved-dose-reviews-20261026/{frontend-final.log,typecheck.log,final-build.log,review-fixes.log,unrelated-reload.txt,changed-creatinine.txt,preservation-final.json,saved-reviews-after-reload.png}. Browser-local receipts are not shared server storage or an authenticated clinical audit; clearing site data removes them. Current source eligibility,24-hour renal-context/creatinine limits and prescription save gates remain in force.
