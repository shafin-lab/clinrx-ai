# Bounded local hemodynamics consolidation

Candidate: `a9fffd9aa2ae933beb9f3f246c5d4551ae7f0b4e`  
Tree: `57717f66a6e358ba1ae5339a87134967894f188e`  
Parent: `db56f7e8164a7a3c46c6c8e17a56c0d9088c2de5`  
Working tree clean at recording; locally committed only. No push, merge, hosted CI dispatch, deployment or external hosting occurred.

## Result

One synthetic patient workspace now connects recorded evidence → exact source/history → immutable correction → separately authored reassessment → exact-note comparison → read-only handover selection review. The gate must be confirmed disabled and patient/encounter scope must match before new writes. Drafts and uncertain saves remain mounted, with exact lookup and explicit same-revision retry. Handover is session-only and does not save, send or schedule a handover. HPI remains optional. No clinical rule, inference, conversion or generated treatment conclusion was added.

The accepted 5191 service/database remain unchanged. The candidate runs on loopback 5193 using a SQLite backup copy of that synthetic database. Production protected execution remains disabled. `health.json` is a fresh implementation-operated service observation; not independent verification.

## Validation and exact commands

Commands ran in `<repo>/frontend` unless noted. Final tests/builds preceded the commit against the committed implementation bytes. `source-hashes.json` records all eleven committed files; `candidate.diff` and raw commit are retained. No clean-archive rerun is claimed.

| Check | Command | Final result / raw log |
| --- | --- | --- |
| Full frontend | `npm test -- --maxWorkers=2` | 639 passed, 19 files, 38.49s; `frontend-final.log` |
| New workspace integration | included in full frontend; 14 cases | Earlier dedicated 14-case pass, 10.66s in `integration-final.log`; final full run includes strengthened unsaved-source guard assertions |
| Default typecheck/build | `npm run build` | passed; `default-candidate.log` |
| Local authoring typecheck/build | `VITE_SYNTHETIC_HOSTED=true VITE_SYNTHETIC_AUTHORING=true npm run build -- --outDir <validation>/candidate-build` | passed; `authoring-candidate.log` |
| Authoring/gateway/storage | from repo: `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 backend/venv/bin/python -m pytest -q -p no:cacheprovider tests/test_synthetic_authoring.py tests/test_synthetic_hosting.py tests/test_guided_authoring.py` | 66 passed, one existing warning, 290.55s; `gateway-regressions.log` |
| Source whitespace | `git diff --check` and `git diff --cached --check` before commit | exit 0 |
| Python syntax | `ast.parse` on `tools/run_evidence_entry.py` | passed |
| Workflow syntax/permissions | Ruby Psych safe YAML load; assert backend/frontend jobs and contents:read | passed; no workflow dispatch |
| Database and gate correspondence | `python3 verify_browser_data.py` (recorded local absolute paths) | exit 0; `browser-data-verification.json` |

Node 24.12.0/npm 11.6.2; Python 3.11.6. Hosted pins remain Node22.13.0. Existing bundle-size warning is nonblocking. No full backend suite or new container validation was needed/claimed for this frontend/launcher/CI increment; backend source/contracts/configuration are unchanged.

## Actual local browser/API exercise

Implementation-operated captured evidence, not an independent uncoached-user or Director live exercise. The original browser build is retained in `browser-pre-final-build/`; its normal-flow captures precede the final narrow-selector CSS and extra unsaved-source guard. Final `candidate-build/` was then installed, reloaded and inspected separately. The 639-test final run and final builds cover both changes.

1. Inspect exact ABG `circulatory_oxygen/1c1f16d9-33d7-40fb-a94f-013a383c9bfc/aeaca128-a674-4dfa-859a-9ab11d2a9368`: pH7.3500, original09:45 sample context, own FiO2/PEEP, unknown quality. Add it to handover and inspect its two-revision history.
2. Correct via exact source handoff and reviewed append. New revision `45797d66-cac9-4f83-9d40-45da73366753`, pH7.3600, ingestion175. Same specimen/time/acquisition; explicitly fictional transcription correction, not a new sample or improvement. Saved identity remains visible during gate-unconfirmed refresh; writes remain blocked until confirmation.
3. Author separate reassessment `circulatory_event/a38d77a7-1aed-4e96-a05d-c467144154a2/1`, ingestion176. Exact baseline `a02f88e1-db04-48a0-89e6-f236016a38a8/1`, intervention `99a26724-026c-4ccc-ac63-c22ddada2664/1`, follow-up new45797 revision. Findings, unconfirmed possibilities and confirmation barriers remain explicit.
4. Compare original note `abae4ef7-74c4-48cc-bb50-f50e9fb151cd/1` (ABGrevision1) with the new note (45797 revision). Original references remain unchanged. Inspect all three ABG revisions. Add new note to handover; earlieraeaca selection is marked historical without successor substitution.
5. Final candidate reload: confirm retained notes, exact comparison and execution-disabled header. At390×844 the document width is390, after correcting long-selector overflow (earlier width561 retained in captures). At1280×1000 document width is1280. Fill an unsaved entry on the final build: navigation and new-source selection are disabled; explicit discard restores navigation. No extra database write occurs. Console error/warning inspection returned no entries. These are targeted views, not all-device/accessibility certification.

DOM, JPEG captures and service metadata are retained under `browser-*` and `server-metadata.log`. The final observed asset paths are `/assets/index-DCa68V-F.js` and `/assets/index-CaTo7ovc.css`; installed files equal candidate build bytes (`candidate-build-hashes.json`). This is not an authenticated complete resource/network trace. The first attempted history wait had a punctuation mismatch; reading the actual loaded DOM confirmed three revisions. The selector API attempt using a label did not match; role selectors succeeded. An attempted Start another entry action during refresh was blocked; it succeeded after the gate was confirmed. No automatic retry was performed.

## Database preservation

`browser-before-rows.json` is the actual174-row baseline exported before this exercise. `browser-after-rows.json` and `browser-after.sqlite3` are later actual after checkpoints; no before SQLite binary is claimed. SQLite integrity passed for candidate and unchanged5191. All174 prior fact rows and both receipts are unchanged; only two new facts, one175→173 predecessor link and sequence174→176 were added. All other tables match. The accepted5191 rows still equal the baseline. `verify_browser_data.py` checks these assertions, exact new payload hashes, original sample/time/context preservation and new-note association. The readable rows contain canonical stored payload strings, not regenerated substitutes.

## Preserved unsuccessful and earlier iterations

`integration-first.log`: three failures/eight passes; two timeouts plus a missing Evidence library control during the test refresh sequence. Their timeout root cause was not established; later focused fixtures reduced rendering load without changing timeout limits. `integration-second.log`: two failures/nine passes because test expectations ignored preserved library filters. Earlier six-failure exploratory output was not redirected to a raw file and is not claimed as a saved artifact. `integration.log`: earlier13-case pass. `frontend-full-first.log`:638passed/one duplicate gate-message query failure; the redundant shared editor header was removed. `frontend-full.log`:639passed before final CSS/guard refinement. Final639pass is `frontend-final.log`. Earlier builds are named separately. Two setup commands ran in the wrong directory: one failed to edit the CSS before an earlier build; one root `npm test` failed with missing script (`root-command-error.log`); neither is final validation. Python YAML loading was unavailable; Ruby YAML validation passed after importing Date. These are not attributed as application defects or environmental timeout root causes.

## Acceptance/evidence reuse and remaining gates

The committed scope document maps reusable components, changed files and acceptance cases. Prior Director C1/R1/F1/F2, db56 local-update and Docker/lifecycle acceptances retain their original exact-source/captured boundaries. No old PR23 CI or old container acceptance is represented as covering this candidate.

Still required before workflow acceptance: Director review, hosted CI for this exact candidate/tree when authorized, and an uncoached new-visitor usability exercise. CI configuration is prepared locally only. No connected protected-execution lifecycle exercise was authorized or performed. The new browser run is normal-flow; save uncertainty, exact lookup and explicit retry are covered by integration/API tests rather than new live fault injection. Durable browser-session recovery remains deferred. Handover selections disappear on reload; it is a review aid, not a durable handover workflow. This does not establish clinical readiness.
