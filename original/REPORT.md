# RF2 F1–F3 corrected implementation

Candidate 757b163f0f56f1343a32455fc0c4427460dfdd71 is one local correction candidate over the reviewed 4429401, retaining the separately tested fetch-receiver correction 84c6482 in its ancestry. No clinical model, persistence implementation, migration, dependency pin, CI workflow or timeout was changed. Only local opt-in RF2 DTO/transport/service/gateway/UI, targeted tests/fixtures and documentation changed.

## Changes

**F1:** History validates the actual outer repository first, then requires pin agreement. A foreign outer repository with a valid local pin returns conflict before evidence. The matching success path and foreign-pin rejection remain covered.

**F2:** New cross-owner RF2 amendments are rejected and routed through the original owner. RF2-owned amount corrections preserve availability and complete unedited source timestamp/clock/basis, interval and other context. Existing exact retained lookup/retry precedes the new admission restrictions; it cannot create another cross-owner amendment. A synthetic pre-fix cross-owner producer reconstruction is explicitly not labelled an archived-producer execution. Separately, the corrected consumer verified both actual captured old note commands against copies of the captured old SQLite database without changing any of its twelve tables.

**F3:** Validation returns each exact selected reference and its actual terminal revision/digest/ingestion/typed record status. The UI provides explicit review; historical or withdrawn/invalid terminal context requires explicit retention acknowledgement. No source successor is substituted and unsupported generic observation quality/withdrawal fields remain unavailable.

Review decisions fit existing carriers: at most 25/32 external entries and 12/32 associations. The strict maximum supported twelve-source probe reports 49,611 fact bytes, 27,560 request bytes and largest entry 2,672 bytes under unchanged limits. Existing request bytes do not acquire a default source_review field.

A new save rechecks the reviewed sources under the same BEGIN IMMEDIATE transaction as append. A later source change blocks the new note; unrelated records advancing the watermark do not invalidate otherwise unchanged sources. Matching retained results return before new review checks. Original pending requests are retained through uncertainty, exact lookup and explicit identical retry.

A definitive source-change rejection is command-bound by request digest and disabled-execution status. Only a validated rejection enters the explicit re-review path; no automatic new request or save occurs. Unknown/malformed responses still remain uncertain. Historical consent resets on explicit re-review.

## Exact-candidate CI

Run 39368985675 passed: **4,350 backend tests**, one existing warning, and **749 frontend tests**, typecheck and both builds. Both checkout logs identify exact 757b163, not the older PR head. See CI-RESULTS.md and logs/hosted-final.log.

## Local checks and exact attribution

- Final complete frontend: **749 passed across 27 files**, 63.55 seconds, using --maxWorkers=2. Final focused: **39 passed / four files**, 4.01 seconds. Typecheck, default and explicit RF2-enabled authoring builds passed. The existing bundle warning remains.
- Final backend focused RF2/correction suites: **32 passed**, one existing Starlette/httpx warning, 52.64 seconds. Earlier broader entry/recovery integration: **57 passed**, 159.21 seconds, before the last richer-context/definitive-rejection refinements; do not label that as an exact-final integration rerun. Exact-final full backend evidence belongs to CI, not the older local run.
- Old-source controls: six failures and one passing foreign-pin control. Four failures stop at the absent new review field; they are not four independent browser failures. A second two-case old-source probe directly demonstrates correction/withdrawal after validation followed by a successful unreviewed append where rejection was expected. These remain failed old-source results.
- One strengthened availability/context test initially supplied a verified clock without its required basis and failed fixture admission. The final fixture supplies the basis; the original failure is preserved. Initial command-path/module-path and sandbox dependency-cache errors remain separate from application failures. No assertions or timeout thresholds were relaxed.
- The existing fetch-binding correction had two failing receiver-sensitive controls, then 31 passing RF2/transport/integration tests and both builds. Its earlier report/artifacts remain separate; no native browser exception capture is claimed.

Local Python 3.11.6, Node 24.12.0/npm 11.6.2. Hosted Python/Node attribution is separate in CI-RESULTS.md. The CI review tag publishes source for exact validation only; PR #23's application head is not changed and no deployment occurs.

## Actual local update and preservation

The old process/frontend were preserved and the candidate installed on loopback port 5201. A database checkpoint was taken before restart and another after eleven actual HTTP read/validation operations. All twelve tables, 182 fact revisions and both retained receipts match exactly. Integrity and foreign-key checks pass.

The eleven operations establish health/execution disabled, current catalog, foreign outer/pin history rejection, matching history, both actual old note lookups, explicit acknowledgement of historical selected sources and stale reviewed-source rejection. No new note or corrected measurement was saved during this runtime check. The raw response contexts are redacted. Browser/localStorage execution is not claimed.

All 1,173 checksums in the previous published evidence package still match. The original accepted repository checkout remains unchanged. Previous RF1/hemodynamics acceptances and parent evidence attribution remain intact.

The stored RF2 sample remains 35.0000→36.0000 mL. User instructions to create 40.0000→45.0000 mL and another note did not establish those saves; this correction does not fabricate them.

## Remaining boundary

RF2-F4 is not included in F1–F3 acceptance. RF2-12 remains open: browser-tool policy prevented a live browser exercise, and API/component tests cannot establish narrow layout, keyboard/focus/scrolling, pointer behavior, accessibility or uncoached usability. No new container, clinical readiness or independent Director acceptance is claimed. General durable browser-session draft/command recovery remains deferred.

Execution remains disabled. No merge, deployment or external hosting occurred. Review is needed on this exact correction candidate; old accepted scopes are not invalidated by the new findings or silently extended to the new source.
