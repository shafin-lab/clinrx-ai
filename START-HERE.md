# RF2 specification review

Revised draft for Director, 19 October 2026. Read [RF2-WORKFLOW-SPEC.md](RF2-WORKFLOW-SPEC.md).

Review one bounded local synthetic milestone: urine/fluid/weight entry → correction/history → clinician-authored renal reassessment → exact comparison → saved mixed-kind handover and reload.

Baseline: `5cb73212ae6104b02bad361886cd9507795d88bf`, tree `7505ff88af8089f2d729fc230b15f3a604c5c9c0`. Preserve accepted RF1-F1 and earlier hemodynamic corrections. RF2 contributes to M8/M9 without renumbering or claiming completion.

Decisions requested:

1. Approve or correct the bounded field/storage mapping, existing CirculatoryEvent use and strict versioned source metadata; no legacy clinical model extension.
2. Check the exact mixed-kind resolver, optional intervention context and retained note references.
3. Check additive handover v2, explicit v1 copy, exact historical restoration and no silent migration.
4. Check uncertainty/retry, repository isolation, bounds and preservation requirements.
5. Check shared-value ownership: reuse existing weight/fluid facts across modules, avoid copying generic weights into circulatory events, distinguish duplicate source submissions from genuine repeat measurements and preserve original correction paths.
6. Check RF2-01 through RF2-12 and the single combined candidate/validation/review boundary.

This publication contains planning documents only. SHA256SUMS.json covers all included documents except itself. The previous local draft and its original checksums remain unchanged under prior-draft/; CHANGES-FROM-LOCAL-DRAFT.diff records the shared-value clarification. Publication establishes accessible review documents, not RF2 implementation, application tests, an application commit or a runtime change.

Implementation requires approval of this exact revision and explicit user authorization. Clinical execution remains disabled; do not implement, merge, deploy, host externally or activate execution during this specification review.
