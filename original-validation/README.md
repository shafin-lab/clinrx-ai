# Comprehensive local demo — validation

Local source: `8d3ce9cec1aa5c843cb25af385735d358fb02a44`  
Tree: `deaeb0e59f520b56a5ddf845f92609a502d42446`  
Branch: `feature/comprehensive-synthetic-demo`; clean working tree. No push, merge or deployment. Accepted PR #23 stays at `17e2064c3f1a1761876e9a42c5c7a131646d465c`.

UI: http://127.0.0.1:5179  
API: http://127.0.0.1:8766  
Running disposable dataset: `/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/comprehensive-demo-local-run/synthetic.sqlite3`.

## Result

- Full backend: **4,223 passed**, one existing Starlette/httpx warning; 583.49 seconds; exit 0.
- Full frontend: **431 passed**; 14.36 seconds; exit 0.
- Typecheck and production build: passed; exit 0.
- New isolated fixture API checks: 2 passed; 7.71 seconds.
- Python dependency consistency: no broken requirements; migration head `m7_0008`.
- Tracked/staged whitespace checks: passed. Clinical/API/execution/model/persistence/migration and transport-decoder sources have zero changes from accepted PR #23.

Backend command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python -m pytest -q -p no:cacheprovider tests` from the repository root. Frontend commands: `npm --prefix frontend run typecheck`, `npm --prefix frontend test`, `npm --prefix frontend run build`.

The suites ran before the local commit was created. Backend/test content was unchanged throughout its full run; the final frontend checks followed the last UI edits. The commit captures that tested working content. Exact final file hashes are in source-identity.json. No hosted CI result is claimed for this local-only branch.

## Live browser and API checks

The actual reviewed frontend/API path was exercised with the execution gate closed: cardiac output and echo inspection, all-15-family listing, FloTrac search, exact calibration support history (revisions 1/2), repository-ingestion timeline, explicit uncertainty/context/unplaced lens, and lookup of real released/withheld fixture receipts. DOM captures and screenshots are retained here. The 390px responsive check reported document/body width 390px with no horizontal overflow; viewport was reset afterward.

The real API returned 26 current items across 15 families and execution_enabled=false. A direct new-preparation request was rejected with 422 without changing fact or receipt rows. Exactly two offline-generated fixture receipts remain. Raw state, receipt responses and the closed-gate proof are retained here; no new connected execution was enabled or performed by browsing.

The launcher performs explicit offline disposable fixture generation before starting the server. Those two stored examples are not production receipts, clinical validation or new actions on page load. The running source configuration remains gated. Patient identities and all clinical assertions are fabricated; device names describe recorded synthetic source context, not integrations.

The local launcher process remains running so the user can explore. Ctrl+C in its terminal stops both child servers; it retains the disposable data/logs. Relaunch using the documented command in docs/COMPREHENSIVE-SYNTHETIC-DEMO.md with a new disposable directory. Existing databases are never reset or overwritten.

Director has separately accepted E1–E3 for the earlier exact isolated lifecycle; that does not independently review this new demo branch. The supplemental acceptance snapshots cover three relevant tables, not every database table. Production execution remains disabled. Durable browser-session command recovery remains deferred.
