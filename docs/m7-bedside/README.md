# M7 bedside integration

M7 now includes a recorded vital-sign panel. See
[VITAL-SIGNS-UPDATE.txt](VITAL-SIGNS-UPDATE.txt) for the latest preview and checks.

The shared patient-workspace integration is now complete in the candidate. See
[SHARED-WORKSPACE-INTEGRATION.txt](SHARED-WORKSPACE-INTEGRATION.txt) for the current
preview, shared-loader behavior, weight recovery checks and verification evidence.
The implementation and validation details below describe the original M7 handoff.

The existing M7 recorded-evidence module now has an integrated bedside view at
`?workspace=hemodynamics`. It uses the existing `CirculatoryClient`, strict
transport decoder and patient-state-v3 service. The evidence workspace and local
patient workspace both link to it. The antibiotic design supplies the muted teal
review layout, four focused questions and adjacent source drawer.

## Implemented in this change

- Four questions: pressure reliability/target, perfusion, working problem and next
  review. These are separate views; target pressure never implies adequate perfusion.
- All 15 existing evidence families, grouped into pressure, perfusion, flow/echo,
  infusion/intervention, fluid-test and full-source views.
- Exact source values, methods, quality, times, original provenance and explicit
  revision history. Source quality is attributed, not a ClinRx validity certificate.
- Patient/encounter/review-window/repository/gate checks before bedside projection.
  Duplicate identities or foreign/mismatched sources withhold that projection.
- Contextual and unplaced evidence stays accessible without entering headline
  in-window observations. Multiple readings show a count and require source
  inspection; no automatic latest/favorable reading selection or clinical ranking.
- Original decimals remain strings. Review-boundary offset comparison keeps the
  fractional lexeme separate; it does not use lossy Date.parse comparisons alone.
- Vasoactive orders, preparation, initiation, rate changes and interruptions retain
  their distinct source meaning. No start event becomes a current running rate.
- Source-linked manual session reviews with required next step, reviewer, rationale
  and next review plan. Optional perfusion/mechanism/session MAP goals are explicitly
  reviewer-entered and unverified. No clinical classification is computed from them.
- Review records retain exact evidence pins and snapshot identity. A changed
  snapshot blocks stale drafts; historical session notes remain labelled. Failed
  retrieval blocks new reviews. Late history responses do not replace a different
  selected source. A session note is not a patient chart record or scheduled task.
- Responsive layout, keyboard focus, explicit loading/error states and accessible
  evidence category controls. The source drawer remains available on narrow screens.

## Specification incorporated, capability activation unchanged

The complete authored M7 v0.1 design package is retained under `specification/`:
609 field definitions, 84 proposed rules, 27 workflows, 25 calculation references,
248 validation specifications and 11 unresolved local clinical policy groups.
These catalogs are design inputs, not an executable clinical rules engine.

This change implements the connected evidence/bedside presentation and manual
session-review parts of that design. It does **not** implement the entire proposed
clinical schema, all workflow backends, numerical profiles or clinical inference.
The current backend records and routes remain unchanged. No new protected
inference execution, source mutation, medical order or device-control operation is
invoked by this view. Existing SyntheticPLVEligibility/1, exact receipts, source
history and closed clinical-execution gate are preserved.

Hospital targets, shock diagnosis, PPV/PLR interpretation, fluid treatment,
individualized dose/concentration conversion, titration, specialty pathways,
clinical alerts, durable clinical notes/tasks and device management still require
the exact approved profiles, authorization and validation in the design package.
No local thresholds, clinical approval or live integration has been invented.

## Validation performed

Story: bedside route → existing typed M7 client → patient-state-v3 API → disposable
synthetic SQLite records → four-question source view → exact history read and
manual session review. No treatment or clinical source write is part of this story.

- Production build/type checking passed. Existing large shared schema bundle
  continues to produce the Vite chunk-size advisory; no new library was installed.
- 19 new projection/workflow tests passed. These include foreign scope, duplicates,
  gate/window/repository mismatch, exact fractional boundaries, unknown/withdrawn
  observations, multiple reading ambiguity, stale drafts, retrieval failure,
  exact history, late response rejection and no clinical execution calls.
- 99 focused frontend/regression tests passed across six files: new bedside,
  existing M7 state/recovery, patient overview, weight entry and renal integration.
- 25 existing backend circulatory API tests passed. One installed Starlette/httpx
  deprecation warning was reported; no backend dependencies were changed.
- Browser confirmed original MAP/lactate/CRT, source context, exact history from
  the backend and a 41-pin synthetic session note. API logs showed successful
  patient-state GET and history POST; no review execution/source write was sent.
- Browser console check returned no warning/error messages. At390px viewport,
  document width matched390px with no horizontal overflow. The viewport was reset.

These are engineering and synthetic workflow checks, not prospective clinical
validation, certified usability or permission for real-patient use. Session notes
clear on reload; the UI states that limitation and does not imply durable charting.

The local preview uses a newly created disposable fixture database and an explicitly
closed execution gate. Existing databases and other module source changes were not
replaced. No synced project source under `sources/` was edited.
