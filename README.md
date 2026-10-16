# Comprehensive synthetic demo — Director review

**[Browse the exact demo source](https://github.com/shafin-lab/clinrx-ai/tree/8d3ce9cec1aa5c843cb25af385735d358fb02a44)** · **[Review its ten-file change against accepted PR #23](https://github.com/shafin-lab/clinrx-ai/compare/17e2064c3f1a1761876e9a42c5c7a131646d465c...8d3ce9cec1aa5c843cb25af385735d358fb02a44)** · **[Source run guide](https://github.com/shafin-lab/clinrx-ai/blob/8d3ce9cec1aa5c843cb25af385735d358fb02a44/docs/COMPREHENSIVE-SYNTHETIC-DEMO.md)**

Application head: `8d3ce9cec1aa5c843cb25af385735d358fb02a44`  
Application tree: `deaeb0e59f520b56a5ddf845f92609a502d42446`  
Source tag: `clinrx-comprehensive-demo-8d3ce9c`

This is a source-and-evidence review handoff, not a hosted website. Director can inspect everything here without Mac access or a ZIP. Running the prototype still requires a local environment using the guide. **Production connected execution remains disabled. Nothing is merged or deployed.** Accepted PR #23 remains unchanged at `17e2064c3f1a1761876e9a42c5c7a131646d465c`. The new demo is not covered by that earlier acceptance.

## Start here

- [All files, with direct links](INDEX.md) and [SHA-256 manifest](SHA256SUMS.json).
- [Original local validation report](original-validation/README.md), [backend log](original-validation/backend-tests.log), [frontend log](original-validation/frontend-tests.log) and [original capture manifest](original-validation/SHA256SUMS.json).
- [Exact-head typecheck log](typecheck.log), [build log](build.log) and [commands/timestamps/exit codes](checks.json).
- [Independent-data-check entry point](verify_evidence.py), [verification results](verification-results.json) and [passing output](verification.log). This supplied verifier is implementation evidence, not Director's independent verdict.
- [Raw synthetic database snapshot](runtime/synthetic-snapshot.sqlite3), [readable table/fact/receipt exports](row-exports/), [original state/receipt responses](original-validation/) and [runtime manifest](runtime/manifest.json).
- [Fresh closed-gate exchange](runtime/gate-exchange.json), [exact request](runtime/gate-request.json), [response](runtime/gate-response.json), and full [before](runtime/gate-before-rows.json)/[after](runtime/gate-after-rows.json) rows of the three relevant tables.
- [Final-source browser captures](browser-final/), with timestamped [capture sequence](browser-final/actions.jsonl).

## What to review

The read-only workspace exposes 26 records across 15 families: cardiac output/index, echo TAPSE/LV EF/LVOT VTI, pressure/PAC/RHC, ECG/rhythm, perfusion, oxygen transport, lactate, vasoactive events and the remaining recorded families. FloTrac/HemoSphere, PiCCO and VolumeView/EV1000 are fabricated recorded source context, not live integrations.

Review usefulness of overview/search/family filtering, exact source inspection, unit-mapping and quality disclosures, contextual/unplaced evidence, bounded correction history, repository-ingestion timeline, and retained released/withheld examples. Featured cards are fixed demo presentation choices, not clinical ranking. Source numeric lexemes and units are preserved; no calculator, clinical threshold or treatment recommendation is added.

The main workspace reads state, history and retained receipts only. The launcher explicitly seeds a fresh disposable database before starting the actual API with its default execution gate closed. Offline setup creates two real protected-workflow fixture receipts. Reading them does not execute a new review. Existing databases are refused rather than reset. Production settings, schema, migrations, dependencies and protected clinical/API/execution sources are unchanged. The old interfaces remain at `?workspace=legacy`.

## Validation and provenance

Reported full local suites: **4,223 backend tests**, one existing warning, and **431 frontend tests** passed. Those suites ran before the local commit was created; the committed content matches the tested working files, as documented in the original report. No new full-suite or hosted-CI result is claimed merely because source is published. Typecheck and build were rerun at the exact committed source for fresh raw logs; both passed.

The original captures include development-stage presentation wording. `final-overview-*` in the original folder is the final overview. `browser-final/` adds fresh exact-checkpoint captures of overview, echo source, all families, support correction history, timeline and both retained examples, so earlier wording does not have to be treated as final UI proof. Original bytes and their manifest are preserved. The original 390px responsive check is retained and its viewport was reset afterward.

The database was backed up consistently through SQLite while the local demo remained read-only; this is a publication-time snapshot, not a claim of a historical binary capture. Raw current-state capture, original state/receipt responses, complete row exports and eight evidence-witness checks match that database. Exported rows recompute both original gate commitments. A fresh real-HTTP preparation request also returned 422 with identical before/after repository, fact and receipt rows. Those snapshots contain all rows of **three relevant tables**, not every database table. The full database and exports cover all tables separately.

The portable stdlib verifier recomputes stored canonical receipt hashes, exact original/terminal references and content digests, latest-at-cutoff rows, repository IDs, original < inference <= final prefixes, ingestion metadata, inference inputs/declarations, state digests and closed-gate row equality. Director should inspect/recompute independently rather than equating its PASS with independent acceptance.

## Browser evidence

| Journey | DOM | Screenshot |
| --- | --- | --- |
| Overview / all-family coverage | [overview](browser-final/overview-dom.txt) | [PNG](browser-final/overview.png) |
| Echo and unresolved source unit mapping | [echo source](browser-final/echo-source-dom.txt) | [PNG](browser-final/echo-source.png) |
| All 15 family headings | [library](browser-final/all-families-dom.txt) | [PNG](browser-final/all-families.png) |
| Exact CAL/1 → CAL/2 correction history | [history](browser-final/support-history-dom.txt) | [PNG](browser-final/support-history.png) |
| Repository sequence timeline | [timeline](browser-final/timeline-dom.txt) | [PNG](browser-final/timeline.png) |
| Retained released receipt | [released](browser-final/released-dom.txt) | [PNG](browser-final/released.png) |
| Retained withheld receipt | [withheld](browser-final/withheld-dom.txt) | [PNG](browser-final/withheld.png) |

## Reproduction and limits

Fetch the source tag or exact application commit, use pinned dependencies and follow the source run guide. Do not enable the API execution gate to browse the demo. To inspect evidence only, download/read the files directly, verify SHA256SUMS.json and run `python3 verify_evidence.py` from this evidence directory; no app execution, signing key or extra Python package is needed.

The captured database and clinical assertions are fabricated. No runtime signing keys, credentials, environment files or unrelated local data are included. Signed state contexts in captured API responses are transient disposable-demo artifacts, not production access credentials. Localhost URLs and absolute paths in the original logs describe the original environment and are not offered as remotely accessible links.

No merge, deployment, release or production activation is authorized by publication or by a future review verdict. Durable browser-session command recovery remains deferred; legacy reload/closure can lose in-memory commands. Clinical validation is not established. Director should return an acceptance-for-preview-preparation or changes-required verdict, distinguishing inspected evidence from a personally rerun browser exercise.
