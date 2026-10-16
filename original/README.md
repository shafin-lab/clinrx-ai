# Expanded synthetic hemodynamic flowsheet — local validation

Local source base: `33c729d944cf5fd0d6302eb2b19c7e73b697538e` (tree `39331029fe076c71c17e18cdf72a7f7714b33e50`), branch `feature/comprehensive-synthetic-demo`. This work is uncommitted and unpublished. `source-sha256.json` and `source/` identify all 24 changed files, including the earlier unreviewed authored interpretation. `tracked.diff` covers tracked edits; new files are separately included in `source/`.

Production execution stays disabled. No commit, push, merge, deployment or gate activation was performed for this increment. PR #23 was not modified. Director acceptance of the prior descriptive explanation does not accept this new source, container or clinical scope.

## What is included

156 current records: the original 41 plus 115 explicitly synthetic additions. HPI remains optional and absent (14 of 15 evidence families present; support for the optional family is retained). The flowsheet presents 150 source controls on 12 UTC source-time columns and keeps two contextual/unplaced records off-axis. Four other evidence items remain in their existing views.

The hemodynamic portion of all seven priorities is represented: integrated measurements and infusion events; explicit orders versus documented delivery; exact linked dosing weight and separately recorded pump rates; interval urine/fluid/blood/drain/CRRT NET removal context; measurement acquisition context; serial perfusion and distinct ScvO2/SvO2 samples; exact intervention links; and source clinician targets, review time and handover. Public Canadian, Australian, UK and US documentation patterns inform structure, not adoption of a current institution's treatment policy. The detailed scope/reference and module-ownership matrix is in `source/docs/SYNTHETIC-ICU-FLOWSHEET.md`.

No forward-fill, clinical calculation, dose conversion, diagnosis, response classification or treatment recommendation is added. Source-reported balances and cumulative totals remain explicitly source-calculated, with incomplete fluid reconciliation disclosed. Nutrition, general patient management and comprehensive organ-system management stay in their respective modules. VA-ECMO/Impella/IABP remain deferred.

The optional `CirculatoryEvent.recorded_interval` and generated transport schema use existing ClinicalInstant boundaries, provenance and limitations. None is omitted, preserving old canonical payloads. Source interval ordering and duration are not inferred. The original database and all 47 original stored fact payloads are preserved.

## Validation

- Full backend: **4,249 passed**, one existing Starlette/httpx warning, 634.45 seconds (`backend-full.log`, `backend-full-result.json`). This run began before the final synthetic CI metadata correction: the four new CI records were subsequently labeled source-calculated with a source calculation method. The only other backend-test edit was renaming one test and adding its CI-label assertion. Core model/schema/application code did not change after the full run began.
- Final focused backend/API against the corrected fixture: **33 passed**, one existing warning, 59.19 seconds (`backend-focused-final.log` and result). This covers canonical round trips, optional interval compatibility, source precision, exact histories, old evidence retention, retained receipts and gate rejection.
- Final full frontend: **511 passed** across 12 files (`frontend-quality-final.log`). Final typecheck, default build and explicit `VITE_SYNTHETIC_HOSTED=true` local build passed. Exact commands, environment additions, exit codes and durations are in `frontend-quality-final-results.json`. Earlier logs are retained and superseded where later changes are relevant. A `--mode hosted-demo` build alone was not treated as proof of the hosted opt-in; explicit flag builds were subsequently run.
- Python 3.11.6; Node 22.13.0; npm 10.9.2. Dependency check found no broken requirements. Captured migration head: `m7_0008`. Syntax/whitespace and unchanged production configuration/execution services/hosting/migrations checks passed (`static-checks.json`). Existing bundle-size warning remains nonblocking. No new hosted CI or container validation was claimed.

## Live API, database and browser evidence

`live-check.json`, `live-state-redacted.json`, `synthetic.sqlite3`, `raw-row-arrays.json` and `readable-tables.json` retain the final synthetic data. SQLite integrity passed. All 156 API facts and expected digests match stored payload bytes. The database has 12 tables, 162 fact revisions and two bootstrap-created retained receipts. Repeated retained lookups returned byte-identical responses. Browser/API reads added no receipt or execution command.

Original all-table row hash remains `91ed2b1b40f44294d65788ea26deedfd487b2a552d58de9665d0eb366016773c`. Final expanded all-table row hash is `273acbe17d027b1836fa893ebb980dcc333fa6d920defdd60f1b4096fbdc02cc`. Commitments include SQLite's sequence table and use sorted table keys, rowid order, compact JSON and SHA-256. The final hash remained identical after browser inspection. The signed API read-context token is redacted; no signing key is included.

`verify_capture.py` recomputes database/API and captured-DOM correspondence: 150 exact revisions in their source timestamp columns, two off-axis records, exact urine history, suspect CO, source-calculated CI context, exact infusion support, distinct venous specimens, unknown assessment quality and source intervention links. `capture-verification.json` records PASS. Supporting captures are named by subject: `flowsheet-dom.txt`, `fluids-dom.txt`, `urine-inspector-dom.txt`, `urine-history-dom.txt`, `dobutamine-inspector-dom.txt`, `ci-context-dom.txt`, `assessment-dom.txt`, `assessment-linked-co-dom.txt`, `goal-dom.txt`, `scvo2-dom.txt`, `svo2-dom.txt`, `suspect-co-dom.txt`, `summary-dom.txt` and PNGs.

The exact-case authored interpretation correctly withholds its old possibilities for the expanded dataset; no replacement clinical interpretation is generated. Source goals are labeled clinician assertions, not system targets.

These are implementation-produced local tests and captures, not independent clinical acceptance. Captures are selected UI states, not a complete timestamped browser/network action trace. Keyboard activation was used for off-screen table controls; this is not a complete pointer/accessibility audit. During iteration, HMR reset an inspector and one label-based automation selector failed; final role-based selection and source states were verified. Earlier phase-two expectations for the prior record count/missing infusion support were updated to the new fixture, and a proposed common-time interval representation failed the existing typed-time validator before it was replaced with explicit ClinicalInstant bounds. No claim is made that those attempts were accepted application data.

The local demo remains on http://127.0.0.1:5179/ with execution disabled. Earlier original and phase-one databases/evidence remain in their separate directories.
