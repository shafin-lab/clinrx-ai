# Local synthetic evidence entry — validation

Source: `5e204af79c370bf61e8676b2c6191e5d08cd7d9b`
Tree: `8294161c6f90f6961c5b651306f497c4dc68d16c`
Base: `d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982`
Local branch: `feature/comprehensive-synthetic-demo`. No push, merge, deployment or external hosting.

## Result and boundaries

Separate loopback workspace: http://127.0.0.1:5185/ . Fresh database at `../evidence-entry-local-run/synthetic.sqlite3`; accepted Docker workspace on 5183 remains separate, reports 156 items and execution disabled. New workspace seed was 156 items / 162 fact revisions / two retained receipts. Browser entry exercises now leave 157 items / 166 revisions / the same two receipt identities. No new clinical inference/preparation/execution/reconciliation route is admitted.

This initial prototype imports complete structured source records under the 15 M7 contracts and offers source selection, numeric correction, reason/actor review, withdrawal, bounded history, immutable append, exact-revision lookup and explicit same-request retry. It does not provide friendly domain-specific new-entry forms, production authentication, clinical validation or durable browser-session recovery. Source context copied into a correction requires explicit review; local actor names are assertions, not verified clinical identities. Optional HPI stays optional. Old authored explanations are not regenerated or approved for edited evidence.

## Checks

- **203 targeted backend tests passed**, 120.75 s, one existing Starlette/httpx warning:
  `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 backend/venv/bin/python -m pytest tests/test_synthetic_authoring.py tests/test_circulatory_api.py tests/test_patient_state_v3_persistence.py tests/test_patient_state_v3_admission.py tests/test_patient_state_v3_admission_compatibility.py -q`
- Earlier combined new-authoring/existing-read-only-gateway run: **51 passed**, 180.38 s. This overlaps the ten new-authoring cases; do not add totals as unique tests.
- **561 frontend tests / 16 files passed**, 37.40 s, in the clean final run:
  `npm --prefix frontend test -- --maxWorkers=2`
- Normal build/typecheck passed with `VITE_SYNTHETIC_HOSTED=false VITE_SYNTHETIC_AUTHORING=false npm run build` in frontend.
- Separate authoring build/typecheck passed with `VITE_SYNTHETIC_HOSTED=true VITE_SYNTHETIC_AUTHORING=true npm run build -- --outDir <isolated-run>/frontend`.
- Existing bundle-size warning remains. No dependency/schema/migration/policy change. Python syntax and staged whitespace checks passed.
- `source-hashes.json` matches all ten committed source/test/documentation files byte-for-byte. Tests/builds preceded the local commit; no clean-archive rerun is claimed. No full-backend or hosted CI run is claimed for this increment.

## Fresh browser exercise and database correspondence

Real same-origin browser → dedicated API → separate SQLite database → decoded save response → refreshed list/history:

1. Fictional pH correction `fs-PH-60/1`, 7.35 → 7.36; successor `0477b2b8-0453-4857-8bbb-6ffb2c2626c6`, sequence 163. Original retained.
2. Complete fictional source import `local-browser-entry-abg/1`, 7.34, sequence 164. Explicit copied-context limitation; not independently acquired evidence.
3. Withdrawal of that imported record, revision `d008c4a3-2074-4579-ad12-527f83f7cf3e`, sequence 165. Import remains retained.
4. **Final build** CO correction `fs-CO-60/1`, 4.60 → 4.61 L/min; successor `2a002ae6-f941-4339-b7df-97e14613cf57`, sequence 166. Preview visibly states value, status, actor and reason; save and two-revision history confirmed. No new measurement or treatment response is inferred. Original source time and suspect quality remain stored.

The earlier pH/import/withdrawal captures preceded the final confirmation-screen text/filter/decoder refinements. They are not relabelled as final-build captures. `final-co-review.*` and `final-co-saved.*` are fresh final-build captures. Screenshots are actual JPEGs with `.jpg` extensions. Original saved captures are preserved.

`database.sqlite3` is a consistent read-only backup made after the exercises. Integrity passed. `tables.json` contains all tables/rows; `database-checks.json` contains original/successor exact payloads and digests for pH/CO. All 157 fresh snapshot fact payloads/digests matched database rows. Original 7.35 and 4.60 records remain. These are after-exercise observations, not a historical before-image of every row. Before/after atomicity, stale rejection, canonical retry and unchanged receipts are established separately by the API/storage tests.

Live lost-response fault injection was not repeated in this browser walkthrough. Backend tests simulate completion uncertainty after a real commit, then exact lookup; frontend tests cover unconfirmed completion, absent lookup, explicit retry and committed recovery. Do not call this a live lost-network exercise. Server metadata is not a complete request/response network trace. The state exports contain ephemeral signed contexts, not signing keys.

## Disclosed development runs

The early explicit-retry UI test exceeded its existing five-second limit in two runs. Its root cause was not established. An isolated run and later full runs passed. The mixed log contains overlapping runs sharing an output path and cannot establish an exact final result; it is retained as inconclusive evidence, with the known timeout visible. The clean final suite has a separate log and completed without another test run overlapping. The retry test now uses the actual visible source filter before selecting the same exact record. No assertion or timeout threshold was relaxed. Investigate further if the failure recurs; do not label it proven environmental.

During implementation, a conflict-response mapping issue, native-fetch receiver issue found by live browsing and test-only TypeScript import issue were corrected. Final logs are the authoritative completion evidence. No independent Director review of this new entry increment has occurred.

Production connected execution remains disabled. The existing accepted Docker image/volume and reviewed artifacts were not rebuilt or modified. No publication to PR #23 was performed for this new increment.
