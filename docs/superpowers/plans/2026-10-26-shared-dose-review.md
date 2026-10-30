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
- [x] 4. Focused + full frontend tests, typecheck/build, fixed checkpoint review. Fix material findings with regressions. Verify copy-only save/change/reload and gate cases in browser; preserved hashes and source records.
- [x] 5. Publish additive assets to existing previews with archived entry HTML and fictional banners. Record verified handoff and show final preview.

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


## Independent checkpoint review and corrections
Read-only reviewer examined f145ba1..c29801f. Two material P2 findings were reproduced: opening a separate prescription draft during an unchanged unsaved assessment could cite the draft context UUID; successful legacy pending-context lookup could unmount its recovery component before releasing the navigation guard. Both now have failing-then-passing Workspace regressions. Prescription detail cites the persisted medicine receipt, and the parent explicitly releases the context guard after pending recovery clears. Fix checkpoint c262a20.

Browser verification also found that unchanged medicines could make Save available before a changed ready candidate was acknowledged. A multi-medicine regression failed on this behaviour, then passed after Save required every ready affected candidate acknowledgment. Context plus selected medicine receipts still use exactly one storage write. Further browser alignment with the approved simple design: matching prescriptions no longer repeat correction actions on each row; a regression failed before this condition and passed afterwards (4d14598). Separate prescription editing remains available for a genuinely differing candidate and through original source Details.

Final review: no critical findings; material findings fixed. No minor findings deferred. Declined-to-judge rulings: authenticated server audit remains outside this browser-local synthetic preview; mobile stays deferred as explicitly requested; clinical guideline/profile content is unchanged. These are existing boundaries, not new readiness claims.

## Browser evidence
Temporary5252 used only a copied fictional SQLite store and copied frontend. Initial3 medicine assessments saved together, with the SQLite hash unchanged. Scripted creatinine3→2.5 and then1.2 results were appended only to this isolated store. At2.5, shared renal reassessment and a single changed meropenem acknowledgment replaced repeated per-medicine checks; ceftriaxone/anidulafungin remained dose-unchanged. One save restored all3 after reload. Corrected build at1.2 also kept Save disabled before changed-dose acknowledgment and held routine suggestions for CRRT; reverting the explicitly fictional support assessment and acknowledging the candidate allowed one shared save. All non-observation source payloads in the copy still match the original demo, proving no prescription/MAR/repository context write. Actual source patient data and exact original browser review keys are preserved.

Current build assets published additively to5247/5249/5251, with old builds/index HTML archived under review-evidence/shared-dose-review-20261026/previous-*-build and old assets retained. No sources/ or backend changes. Existing fictional labels and original25mL/min patient values on5249 remain. Verification and final publish checks continue below.


## Final release
Final code checkpoint dd90926 (source-condition detail preservation after 4d14598 same-dose CTA cleanup). Current frontend suite **1,665 passed, 3 skipped**, 82 passing files and2 skipped. Typecheck, full-feature production build and git diff --check pass. Existing large-chunk warning remains. No backend, executable profile, NCDC library, synced source or patient database change.

Readable dose source links, initiation text and applicability conditions are retained in Details & history (regression RED→GREEN, focused14 passing); keeping the main chart concise does not drop these reference conditions. Source-history and given/held/missed MAR remain accessible. Current unchanged prescription rows do not display redundant correction buttons; differing reviewed candidates still open an explicit correction draft referencing a persisted review receipt.

Published release assets additively to existing5247/5249/5251; old hashed assets and entry HTML archives retained. Original5246 unchanged. Original populated5249 still has creatinine3mg/dL, CrCl25 and all3 prior browser medicine reviews restored under the new shared chart without repeated checks. No new review save was made in an existing patient origin during this pass. All4 original SQLite stores have baseline SHA256 and integrity ok, including the existing creatinine-change walkthrough. See preservation-final.json. Temporary5252 tab closed/server stopped;3 existing preview tabs kept. No worktree or original files deleted; local branch retained as explicitly requested preservation scope.

Screenshot: review-evidence/shared-dose-review-20261026/shared-review-chart.png. Published example: http://127.0.0.1:5249/?workspace=antibiotics&antibioticView=patient&reviewBuild=shared-review-dd90926 . The previous changed-creatinine5251 walkthrough also serves the updated assets. Browser-local assessments remain separate from repository clinical records; clearing site data removes them. Authenticated shared audit and mobile remain outside this completed scope.
