# Guided local evidence entry and reassessment — 18 October 2026

Application: fa8ce7dfba52af169c6f474dbd0826d747884945
Tree: cda06aecf68da72b64e998fc446eadbf2881d64e
Parent: 5e204af79c370bf61e8676b2c6191e5d08cd7d9b
Local branch: feature/comprehensive-synthetic-demo

Local workspace: http://127.0.0.1:5191/
Disposable database/build: ../guided-entry-local-run/
The accepted Docker demo on 5183 and earlier authoring workspace on 5185 remain separate and unchanged. No push, merge, deployment, hosting or production gate activation occurred. This successor is implementation evidence, not Director acceptance or clinical validation.

## Changes

- Guided, one-record-per-append forms for BP/MAP; ABG/oxygen/lactate; CO/CI; broader echo including LVOT VTI, RVSP/PASP and qualitative findings; infusion events; and perfusion. Full source import remains available for all 15 families. HPI and TAPSE are optional.
- Reassessment records a clinician-authored question, exact baseline/intervention/follow-up selections, findings, unconfirmed possibilities, uncertainty and an optional review plan. It saves a descriptive event with stage-labelled references and exact associations under existing contracts. It is not a dynamic-test classification, protected inference, diagnostic engine or scheduled task.
- Director F1: JSON and numeric shortcut now edit one authoritative draft. Raw strings pass to existing normalization; no rounding/conversion. Tests cover JSON-only input, shortcut/interleaved editing and the submitted final fact.
- Director F2: corrections and withdrawals retain reviewed upstream calculation dependency edges and calculation_inputs. UI regressions check exact preservation. Real API regressions admit both and continue rejecting missing/mismatched dependencies without writes.
- Gate confirmation is conditional, failed refresh blocks writes, older refresh responses cannot replace a newer snapshot, and source-row selection compares exact revisions. Read-only recovery preserves the pending draft.

## Checks and attribution

Python 3.11.6; Node 22.13.0; npm 10.9.2.
Commands were run from /Users/mohammedshafiqshajahan/Documents/clinrx-ai (frontend commands from its frontend directory). The pinned Node directory was prepended to PATH.

1. Targeted real API/storage and gateway:
   PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 backend/venv/bin/python -m pytest tests/test_guided_authoring.py tests/test_synthetic_authoring.py tests/test_synthetic_hosting.py -q
   backend.log: 65 passed, 237.84 seconds, one existing Starlette/httpx deprecation warning. Exit 0. Backend application code is unchanged; new guided fixture inputs are matched by frontend builder tests.
2. Full frontend: npm test -- --maxWorkers=2
   frontend-final.log: 588 passed across 17 files, 43.36 seconds, exit 0. This preceded the final additional submission assertion within an existing test.
   frontend-exact-head.log records the subsequent full run after the local checkpoint, including that assertion. Its final outcome is separately recorded in validation.json.
3. Focused final: npm test -- --maxWorkers=2 tests/evidenceEntry.test.tsx tests/guidedEvidence.test.ts
   focused-final.log: 32 passed, 7.24 seconds, exit 0. Includes the final submission assertion.
4. Authoring build:
   VITE_SYNTHETIC_HOSTED=true VITE_SYNTHETIC_AUTHORING=true VITE_PATIENT_ID=synthetic-p1 VITE_ENCOUNTER_ID=synthetic-e1 VITE_REVIEW_START=2026-10-08T08:00:00Z VITE_REVIEW_END=2026-10-08T10:00:00Z npm run build -- --outDir <mirror>/guided-entry-local-run/frontend
   authoring-build-final.log: typecheck/build passed, exit 0.
5. Normal build:
   VITE_SYNTHETIC_HOSTED=false VITE_SYNTHETIC_AUTHORING=false npm run build
   default-build-final.log: typecheck/build passed, exit 0. Existing bundle-size warning remains.
6. npm run typecheck: typecheck-final.log, exit 0. git diff --check and staged whitespace checks passed.
7. python3 verify_browser.py: browser-verification.json, PASS, exit 0.

Earlier attempts are not silently relabelled:
- Initial generated-vector backend checks reached successful admission and append but then 12 cases failed because the new test referred to nonexistent execution_receipt instead of the actual tables. The test now compares every unaffected table, including circulatory_execution; all 65 final checks pass. The initial console result was 12 failed / 12 passed, 68.82 seconds. No application rejection was reported in those twelve failures.
- First startup on 5187 stopped because that port was already in use; launcher.log retains it. No existing service was stopped.
- Startup build on 5191 initially failed two strict TypeScript checks (unknown React node and narrowly typed binding access). launcher-5191.log and ../guided-entry-local-run/build.log preserve the failure. Those typing issues were corrected before final authoring/default builds. The already seeded fresh database was preserved, not reseeded; server.log records its explicit local startup.
- Earlier baseline parallel timeout uncertainty remains unresolved. Current passing runs use the same bounded concurrency of two workers, with no timeout/assertion relaxation.

## Browser-to-API-to-storage exercise

The browser operated the real loopback authoring UI on 5191. Seven guided appends were reviewed and explicitly confirmed: MAP 71.00 mmHg; arterial pH 7.3400 with its own 40% FiO2 / 5 cmH2O PEEP; CO 4.700 L/min with suspect quality; an earlier source-calculated RVSP estimate 45.00 mmHg; documented dobutamine rate change 2.50 mcg/kg/min with unknown dosing weight; capillary refill 3.00 s; and a descriptive reassessment linking the exact new CO, infusion and perfusion records.

before.sqlite3 / after.sqlite3 and corresponding row exports capture actual checkpoints. The independent local data-only verifier checks:
- All 162 original fact rows remain byte-for-byte equal at the stored row/string level; seven new rows give 169 fact revisions / 163 assembled items.
- All other tables except the expected sqlite_sequence counter remain equal, including both retained clinical receipts and their payload digests.
- All 163 captured API facts equal stored payloads with matching digests, scope and ingestion sequences.
- Exact reassessment stage references exist and match all three associations.
- execution_enabled remains false. Unknown clock/identity/availability context and suspect CO quality remain explicit.

browser-*-review.txt and browser-*-saved.txt are UI captures; browser-reassessment-form.txt captures selections. reassessment-saved.jpg is the full-page capture and reassessment-view.jpg the viewport capture (extensions reflect actual JPEG bytes). Inspector disclosure was not expanded for every record; captured context comes from the readable pre-append review plus stored/API data. Server logs are request metadata, not complete request/response bodies. This is implementation-operated browser evidence and subsequent API/database correspondence, not an independently witnessed live session or a complete authenticated browser/network trace. No live delivery fault was injected for this new guided increment; inherited recovery is covered by regression tests.

Raw before/after state responses include ephemeral local signed read-context tokens. These local originals are preserved; do not publish them unredacted. No signing key is stored in this evidence. Future publication must preserve originals and separately document token redaction.

## Limits

No production/backend schema, policy, migration, dependency or Docker packaging change. No full backend suite, hosted Actions run or new container validation is claimed. No Director acceptance is claimed. Actor/source assertions are not authentication. New records have unresolved identity, raw-unit and drug mapping; clocks default unknown. Source times may consequently be unplaced. Advanced editing is still needed for exact dosing-weight/pump support, detailed indexing/calibration and explicit calculation inputs. Multi-analyte atomic entry and reconstruction of guided fields from a normalized source draft are not implemented. Durable pending-draft recovery across reload/closure remains deferred. Existing execution gates stay closed.
