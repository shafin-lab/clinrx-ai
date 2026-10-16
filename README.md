# Comprehensive synthetic demo — local hosting preparation

Source: `28496c46494dcafc5440b92712eab382cd3c80de`  
Tree: `00aa087cce492bd94d4c36c1e0d4299d79fa7d89`  
Parent / Director-accepted preparation baseline: `8d3ce9cec1aa5c843cb25af385735d358fb02a44`  
Branch: `feature/comprehensive-synthetic-demo`; working tree clean.  
Main remains `46267e072be915c6b204fb0a127342032a2b88b1`.

No push, merge, deployment, automatic preview trigger, production configuration
change or production execution activation occurred. The temporary test gateway
and its browser tab were stopped after verification. The original local demo
was left running. Director's baseline review is retained separately in
`director-baseline-review.txt`; it does not accept these new hosting changes.

## What changed

- Separate single-origin static/ASGI gateway for only synthetic M7 state, bounded
  history and the two retained examples. Other API routes and files return 404.
- Explicit hosted frontend mode accepts only its page origin, requires external
  HTTPS (loopback HTTP for local validation), and blocks non-read operations
  before transport. Default loopback behavior and response validation remain.
- Same-origin protection cookies are permitted only in hosted mode. This is not
  authentication; platform protection must cover both UI and API before sharing.
- Legacy tools are hidden and direct legacy navigation is blocked in hosted mode.
- Server gate is explicitly false, independent of inherited production settings.
- Container recipe creates fixtures offline, runs non-root with one worker, and
  does not seed on API startup. No real data, external device or production key.
- Director's narrow-screen inspector finding: selecting a source moves focus to
  its inspector; closing returns focus to the triggering card.
- Director's configuration finding: loading/error states do not claim confirmed
  gate closure; an enabled-gate response blocks browsing with a visible warning.

See `source/docs/SYNTHETIC-DEMO-HOSTING.md` for the local run recipe and release gates.

## Final validation

| Check | Result |
| --- | --- |
| Full backend | 4,243 passed; one existing Starlette/httpx warning; 693.78s pytest elapsed |
| New hosting regression cases | 20 included in the full backend suite |
| Full frontend | 443 passed; final run on Node 22.13.0 / npm 10.9.2 |
| TypeScript | Passed |
| Default frontend build | Passed |
| Explicit hosted build | Passed, clean output directory |
| Python / dependencies | Python 3.11.6; pip check passed |
| Syntax / whitespace | Passed |
| Fixture migration | m7_0008 |
| Real local HTTP | State, history and both receipts load; prepare/execute/reconcile return 404 |
| Browser | CO/CI, echo, 15 families, CAL history, retained outcomes, legacy blocking |
| Final keyboard/mobile | 390×844, no horizontal overflow; inspector focused in viewport; focus returns |
| Desktop viewport | 1280×720, no horizontal overflow |
| Restart | Both receipt response bodies byte-identical; stale context rejected; rows unchanged |
| Data stability | All rows in all 12 tables unchanged after probes, browser journeys and restart |

Backend checks ran on the working content before local commit creation. Backend
and backend-test files did not change during/after that run; the final committed
files and hashes are exported under `source/`. Final frontend tests, typecheck
and both builds additionally ran after the commit with Node 22.13.0 / npm 10.9.2.
Earlier Node 24.12.0 / npm 11.6.2 checks are explicitly retained as `node24-*`.
No hosted CI for this new checkpoint is claimed.

`*.json` beside each final test/build log records exact commands, working directory,
start time, elapsed time and exit code. `run_checks.py` and the HTTP/restart probes
record the local harness; their paths target this Mac. `verify_evidence.py` is a
portable, data-only verifier and never starts an application or runs probes.

## Evidence map

- `source-identity.json`, `source-commit.txt`, `source.patch`, `source/`: exact identity and changes.
- `backend.log`, `frontend.log`, `typecheck.log`, `build.log`, `hosted-build.log`: final logs.
- `http-exchanges.json`, `*-request.json`, `*-response.json`: direct HTTP evidence.
- `fixture-snapshot.sqlite3`, `hosted-synthetic.sqlite3`, `rows-*.json`: database/row evidence.
- `restart-check.json`, `*-after-restart.json`: restart, retained bytes and stale context evidence.
- `final-browser/`: final source desktop/mobile captures, viewport/focus metadata, DOM and empty console log.
- Root-level `browser-*` captures: earlier hosting-stage captures, before the two Director UI fixes.
- `hosted-dist/`: final Node 22.13.0 compiled read-only website, not published.
- `SHA256SUMS`: file integrity manifest; no signing keys or environment dumps are included.

The browser walkthrough used the real loopback HTTP gateway, not a mocked API.
The enabled-gate rejection was exercised in frontend regression tests; no live
server gate was enabled. The mobile focus capture shows the inspector inside the
390×844 viewport and focus returning to the exact source button on close.

## Remaining before external sharing

Docker is unavailable on this Mac command path. The container recipe has NOT
been built/run; direct local application checks do not establish container startup.
The final frontend build was tested with the intended Node version, but the Linux
image and platform runtime still require verification.

No HTTPS external origin, hosting account/project, access-control flow, fresh
external visitor, public reachability, provider cost/duration, or hosted restart
was exercised or approved. Local restart keeps the same synthetic database; a
replacement container starts from its packaged fixture. Ephemeral state-context
keys require refreshing state after process restart. Durable command recovery is
still deferred.

Director must review this new hosting source/evidence; the user must then
separately authorize the named hosting target, access, cost and duration before
any deployment. Verify the actual protected URL and complete the live guided
checks before giving a friend the link. Production execution remains disabled.
