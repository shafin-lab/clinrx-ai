# Shared Dose Review Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline with TDD and one fixed-checkpoint independent review.

**Goal:** One shared assessment save, compatible confirmations retained, prescription changes separate.
**Architecture:** Explicit scoped browser context assessment feeds the existing renal model. One strict append-only group log stores context plus selected medicine receipts atomically; old logs read without modification. A controlled shared chart replaces the two separate review forms.
**Tech Stack:** Existing TypeScript/React, Web Locks/localStorage, signed snapshot/history API.
**Spec:** docs/superpowers/specs/2026-10-26-shared-dose-review-design.md

## Global constraints
No sources/ edits, backend/profile changes, original patient-store writes or destructive preview replacement. Keep old assets/receipts/recovery accessible. Browser-local context is explicitly not a repository clinical fact or shared audit. Current binding/time/AKI/KRT/safety gates and explicit prescription correction stay intact. Mobile deferred.

## Tasks
- [x] 1. RED→GREEN scoped context tests: explicit changed-result reassessment, exact pin/base-context/scoping, earlier views, expiry, AKI/KRT/invalid sources. Add optional ContextAssessment to automaticRenalModel; calculation and current sources remain authoritative.
- [x] 2. RED→GREEN strict atomic shared log and legacy reads: one write for multiple order reviews, no partial/quota/cross-tab/queued save, malformed bytes and scope separation. sharedDoseReviews.ts consumes existing SavedDoseReview validation and dependency evaluation.
- [x] 3. RED→GREEN clinician workflow: shared context once, initial checks only where missing, one Save reviewed assessment, reload, changed creatinine old/new, no repeated compatible checks, separate correction, preserved MAR/history. useSharedDoseReviews + SharedDoseReviewPanel; controlled PrescriptionChart keeps history/details.
- [ ] 4. Focused + full frontend tests, typecheck/build, fixed checkpoint review. Fix material findings with regressions. Verify copy-only save/change/reload and gate cases in browser; preserved hashes and source records.
- [ ] 5. Publish additive assets to existing previews with archived entry HTML and fictional banners. Record verified handoff and show final preview.

## Review focus
- Local context cannot override ambiguous/unbound/stale sources or a later repository context correction.
- Batch save revalidates every reviewed medicine/history and context after lock acquisition; one write cannot partly approve.
- Changed source evidence resets only incompatible confirmations; unsupported medicines never inherit a reviewed dose.
- Pending legacy source recovery remains accessible; valid old reviews survive without rewriting old keys.
- Receipt provenance stays truthful when a separate prescription draft opens; past MAR never changes.

## Ledger
Baseline f145ba1, tracked tree clean. User explicitly approved the interactive design and requested implementation; no further design gate. Reuse existing owned candidate checkout. Four existing patient-store hashes and all three current static roots archived before work. Execute inline; one independent read-only reviewer after fixed checkpoint.

Pre-flight interfaces: ContextAssessment is an explicit browser review, separate from repository context facts; automaticRenalModel(catalog, assessment?) retains source gates. SharedAssessment groups context and per-order SavedDoseReview receipts; appendSharedReview performs one locked storage write. useSharedDoseReviews controls the existing chart; SharedDoseReview supplies the shared context and single footer. Existing RF2 pending context recovery still mounts when pending bytes exist. Parent prescription selection now includes shared-assessment identity to invalidate a separately opened draft after another local review.

Tasks1–3: new tests observed RED for missing context/log/shared workflow, then GREEN. Context plus existing renal model29 pass, pure log/context16 pass, focused UI/log/context27 pass, queued-hook5 pass; typecheck passes. Added one browser-assessment ID to the separate prescription draft detail so its explicit local context provenance remains visible alongside actual repository source pins. First-time missing medicine confirmations stay visible until save, compatible confirmations remain hidden under history. Full suite pending.
