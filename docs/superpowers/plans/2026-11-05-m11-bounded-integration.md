# M11 bounded integration and usability implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement inline, then one fresh whole-branch reviewer.

**Goal:** Make the larger shared patient load reliably and simplify M11 without losing evidence.
**Architecture:** Keep existing typed sources, pins, cutoff and2MiB transport guard. Read shared RF2 and a cutoff-pinned antimicrobial slice separately; keep legacy combined API. Add focused GI presentation helpers only.
**Tech Stack:** Existing Python/FastAPI/SQLite, TypeScript/React, pytest/vitest and native desktop browser.
**Spec:** docs/m11-gastrointestinal/BOUNDED-PASS.md

## Global Constraints
- Preserve current8DBs,3served builds and browser review origins; disposable copy/new origin only.
- No raising response limits, truncating sources, new dependency or migration; no clinical advice, mobile orM12.
- Exact repository/patient/encounter/window/cutoff/digest checks remain fail closed; keep legacy combined endpoint.
- Inline implementation with one final independent reviewer; retain ledger/evidence under preservation instruction.

## Review Focus
- Concurrent repository append between the two reads must not mix cutoffs or lose the earlier exact snapshot.
- Unknown, tied, bounded and fractional timestamps must not hide or falsely replace another finding.
- Mixed known/unknown critical flags and interference/conflicts must stay attributable to affected values.
- A failed/substituted antimicrobial response must not appear as current beside confirmed RF2 evidence.
- Competing editors and post-commit response loss must retain one pending owner and never duplicate a source/review.

### Task1: Bound shared composition without dropping evidence
**Files:** backend/app/services/antibiotic_chart_service.py, backend/app/demo/antibiotic_gateway.py, backend/app/services/renal_fluid_entry_service.py, frontend/src/api/antibioticClient.ts, frontend/src/demo/usePatientEvidenceState.ts; tests/test_antibiotic_chart.py and new frontend/tests/antibioticSharedCatalog.test.ts.
**Interfaces:** Produce read-only GET synthetic-antibiotics/micro with required repository/cutoff plus review window, returning existing MicroStateResponse. Produce AntibioticClient.sharedCatalog(start,end), returning existing AntibioticBundle only after matching RF2 and micro. Existing catalog/action methods unchanged.
- [x] RED: micro route currently404/403; test exact cutoff before a concurrent append, foreign/future/partial pins, origin denial, unchanged legacy endpoint and payload cap.
- [x] RED: UTF8 compact-wire boundary rejects only actual over-limit body; no widened limit.
- [x] RED: sharedCatalog calls RF2 then micro with exact cutoff and rejects mismatch/failure/partial bundles. Hook uses sharedCatalog.
- [x] GREEN minimal implementation; run pytest test_antibiotic_chart and focused transport/shared-patient tests; prove larger copied fixture completes with all identities and same cutoff.
- [x] Commit verified task.

### Task2: Latest-first findings and concise lab qualifications
**Files:** new frontend/src/gastrointestinal/GIOverviewFindings.tsx and GIResultQuality.tsx, existing GastrointestinalWorkspace.tsx/laboratoryPresentation.ts; new frontend/tests/gastrointestinalUsability.test.tsx and existing qualifier tests.
**Interfaces:** Present groups by exact category/title, latest exact time(s) primary, earlier source cards expandable, uncertain-time cards retained. Summary only unknown critical-flag statuses once per report set; all actual warnings stay inline, source/history unchanged.
- [x] RED: same-label earlier observation moves to details without source deletion; distinct titles, tied/exact-fractional/unknown times retained correctly.
- [x] RED: repeated unknown flag wording becomes one summary with exact result/report attribution; critical/interference/conflict stay inline and complete original/history retains qualifiers/comparators.
- [x] GREEN minimal helpers and scoped layout; run GI suite and full frontend/typecheck/build. Commit verified task.

### Task3: Populated combined workflow, native recovery and handoff
**Files:** docs/m11-gastrointestinal/BOUNDED-HANDOFF.md plus ignored test-copy seed/harness/evidence only.
**Interfaces:** Same typed reports across M10/M11/overview; no product-only test endpoint/control.
- [x] Seed isolated larger respiratory+GI case with one PT/INR report and procedure; compare exact source IDs/digests across views, dates/correction/withdrawal and unrelated source sets.
- [x] Build separate frontend/launch unused loopback port; retain old preview. Native two-tab source pending ownership plus deliberate503 after commit, reload/exact lookup, one source append. Native lock-driver tests queued review ownership, release and reload.
- [x] Freeze source checkpoint; fresh read-only whole-branch review and regrade/fix Important/Critical once with RED/GREEN tests.
- [x] Run full maintained suites/typecheck/default+configured builds; final desktop on corrected build; hash/integrity original8DBs and3builds unchanged. Update handoff; main-work verification remains awaiting acknowledgement. Keep mobile deferred andM12 untouched.

## External coordination status

- [x] Resolve verification ownership. ClinRx main work did not undertake the cross-chat review. The user explicitly authorized independent verification instead; no joint verification is claimed.

## Follow-up GitHub integration

The user has authorized source-only publication and merge after independent verification and green exact-head CI. Keep all previews, patient stores and browser review storage unchanged; preserve rollback/evidence assets. No deployment or M12. Record the actual PR, head, tested/merged tree and preservation result after integration.
