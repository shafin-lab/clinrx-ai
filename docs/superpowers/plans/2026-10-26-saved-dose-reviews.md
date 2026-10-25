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
- [ ] RED dependency/log tests: reload, separate scopes/courses, unrelated facts, relevant values/product/treatment/culture/profile/history changes, lower cutoff/earlier view, strict malformed storage and queued/concurrent saves.
- [ ] Implement pure dependency groups and strict bounded append-only persistence (`savedDoseReviews.ts`).
- [ ] RED workflow tests for saved restoration, specific changed-input review, compatible check preservation, history failure, no silent order writes.
- [ ] Add a chart review hook (`useSavedDoseReviews.ts`), explicit save/reviewer/receipt UI, and bounded history hydration for saved reviews in `AntibioticWorkspace.tsx`.
- [ ] Run focused and complete frontend tests, typecheck/build. Commit fixed checkpoint and obtain independent review; fix material findings.
- [ ] Verify save/reload/change/irrelevant-update in an isolated populated copy, preserve hashes of existing stores, publish assets with rollback available, show updated preview.

## Review focus
Stale approval at lock acquisition; hidden cross-tab changes; persisted dose bypassing recomputation; source scope/time rollback; history hydration changing dependency sets; missing clinical evidence; updates to unrelated medicines; preserving original orders/MAR and malformed bytes.

## Ledger
Baseline `fbc1c72`; tracked tree clean. Current main and populated-demo builds archived; database hashes recorded before work. Inline implementation, one independent review at a fixed commit. Browser-local storage is the bounded preview implementation; shared authenticated audit remains future scope.
