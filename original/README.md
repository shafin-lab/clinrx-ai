# RF1 bounded local renal/fluid milestone

Approved specification: `7fa529dd276ceb140700760a358cf3493b44e85b`.
Application baseline: `b4194447829f060387b816437694af9f6c0cb60e`.
Local candidate: `c2d58e4c8d52d2ceeddd57881365cc5f76cdf74f`, tree `960105b34b302648190fa40630725573e893edce`. Working tree is clean. All 20 changed-file bytes match the tested-source manifest and committed blobs. Tests/builds preceded the commit against these bytes; no clean-archive rerun is claimed. Final combined results are in `validation/final-results.json`.

## What this adds

One optional **Renal and fluid review** tab in the existing synthetic patient workspace. The shared loader publishes creatinine originals and the existing circulatory assembly together, at one repository/patient/encounter/window/cutoff. It uses bounded raw observations rather than relying on v1 projections that omit missing/unplaced records. Both reads share aggregate retrieval accounting, and the complete combined response has the existing configured response-size cap.

The tab preserves raw units, source event versus recording times, missing/unplaced observations, conflict/uncertainty, terminal identity and exact correction history. Source event time is not promoted to specimen collection time. Generic observations gain no withdrawal, suspect-quality, specimen or collection-time fields. Existing circulatory records supply the typed withdrawal and suspect-quality examples.

Urine/fluid point events, intervals, recorded totals, reported balances, CRRT net removal and dosing weight stay distinct. A challenge volume is not added to an interval total. No automatic balance, hourly urine rate, conversion, creatinine trend inference, eGFR, AKI staging, diagnosis, target or recommendation is introduced. Renal entry and mixed-kind notes/handover remain unavailable.

The opt-in loopback gateway adds only RF1 composite/history reads to the existing isolated hemodynamics authoring gateway. Existing hemodynamic entry routes retain their prior separate role; RF1 itself adds no writes. Default production routes, read-only Docker gateway, legacy clinical models, migrations, dependencies and execution configuration are unchanged. Preparation, new execution and renal-write paths are unavailable through this gateway. The service refuses an enabled execution configuration rather than falsely labelling it disabled.

## Local workspace and preserved data

[Open RF1 locally](http://127.0.0.1:5197/), then select **Renal and fluid review**. The original workspace on 5195 and its database were not replaced.

The runtime uses `synthetic.sqlite3`, a disposable copy of the existing 167-fact synthetic episode. Explicit fixture setup adds eight revisions: one creatinine correction, two missing/conflicting observation examples and five interval/withdrawal examples. The existing two creatinine sample IDs and all existing fluid IDs are reused. Startup does not seed or reset anything. The separate initial failed-fixture copy is not this final runtime or acceptance dataset.

At review cutoff 175 the runtime retains four terminal creatinine observations and 164 circulatory items. Its original 167 facts, assisted MAP/note journey and both retained receipts remain unchanged. Explicit RF1 fixture appends precede the read-only journey; they are not presented as reads or unexplained writes during validation.

## Combined validation and attribution

- `validation/commands.json`: exact commands, working directories and RF1 flags.
- `validation/environment.json`: versions, dependency consistency and migration head with exit codes.
- `validation/tested-files.json` and `source/`: complete changed-source/test hashes, Git blob identities and copied bytes.
- `validation/backend-focused-final.log`: 16 RF1 API/storage checks, including raw missing/unplaced observations, exact historical replay, no successor resurrection, shared aggregate bounds, combined size rejection, gate closure and all-table preservation.
- `validation/frontend-full-complete.log`: final full frontend, 696 passes across 22 files, unchanged five-second timeout and `--maxWorkers=2`.
- `validation/default-build-final.log`, `rf1-build-final.log`, `typecheck-complete.log`: successful builds/typecheck; existing bundle-size warning retained. Final build flags explicitly enable synthetic-hosted, authoring and RF1. These are local builds, not a new Docker image or deployment.
- `validation/backend-full.log`: **4,318 passed, one existing warning, 1,058.32 seconds**, exit 0. This includes all 16 new RF1 API/storage regressions and existing Kernel/M5/M6/M7/recovery behavior.

Earlier attempts remain disclosed in the raw logs. The first RF1 test found that the proposed sample IDs duplicated two samples already in the ICU seed; final fixture setup now reuses those original identities. Initial new-test type imports and quantity rendering were corrected. Vite initially lacked sandbox permission for its temporary file; the permitted run is separately logged. After inspector focus/return-focus was added, one full frontend run had a five-second navigation-test timeout (695 passed), followed by a focused run with a real-panel timeout (20 passed). The navigation test now isolates unchanged heavyweight screens while retaining the real renal panel, shared hook/client and assertions. The final full run passes without timeout or assertion relaxation. This passing run does not by itself establish every contributor to the earlier timing variation.

## One browser-to-real-API journey

The implementation-operated journey loaded the composite, opened the corrected creatinine sample and its original/corrected history, closed the inspector with return focus, inspected the urine-gap source interval, checked a 575×823 layout, returned to hemodynamics and reopened renal review without another state load. Browser errors/warnings were empty. This is assisted implementation validation, not independent uncoached usability.

Final captures are prefixed `final-`. Earlier captures/builds remain separate and are not relabelled as final. All `.jpg` captures have actual JPEG bytes. Complete DOM/AX text supplies fields outside individual screenshot viewports; no image is claimed to show every record or disclosure simultaneously. The narrow layout records document width 575 with table overflow contained in 555-pixel regions. This is the recorded viewport/interaction, not certification of all devices, touch behavior or accessibility.

`evidence/events.jsonl` and its request/response JSON files are recorded by the local wrapper around the actual application. Signed context fields are redacted and JSON formatting is changed for inspection; these are value-preserving redacted bodies, not byte-identical raw responses or an authenticated complete network trace. Signing keys and the private initial unredacted helper response are excluded from review artifacts. Events 1–6 belong to the initial pre-focus-polish build; events 7 onward load the final build. The final composite/history/interval responses are events 10, 11 and 12. The verifier reports final-build correspondence separately from the aggregate across both iterations.

`evidence/before.sqlite3`, `after.sqlite3`, `final.sqlite3` (after the rejection probes) and all-table row exports establish the read-only database interval. `verify_readonly.py` independently recomputes canonical content/digests, exact selected references, scope/cutoff and ingestion correspondence against those actual SQLite bytes. The verifier performs data checks only, not application/tests execution. Both snapshot integrity and foreign-key checks pass. All 12 tables, 175 fact revisions and two receipts are unchanged; all 167 prior facts and both prior receipts match the original workspace database.

## Acceptance map and remaining boundary

RF1-01 common scope/cutoff: composite validation and one shared loader; RF1-02 original/corrected samples: exact history; RF1-03 context/units: missing, unplaced and unlike-unit examples; RF1-04 intervals: zero/missing/gap/overlap source records; RF1-05 no double counting: distinct challenge/interval/reported total presentation; RF1-06 RRT/weight: source-purpose disclosures; RF1-07 history: terminal outside-window successor and prior-cutoff replay; RF1-08 M1/drafts: existing full regressions plus unchanged mounted editor; RF1-09 closed execution: gateway rejection and no-write snapshots; RF1-10 coherent use: captured read-only journey and navigation.

Independent implementation review and exact-candidate hosted CI remain outstanding. No new container acceptance, clinical validation or general durable browser draft/command recovery follows. This package is prepared for one combined Director review; unchanged acceptance scopes do not require more isolated ABG/MAP walkthroughs.

Execution remains disabled. No remote source publication, merge, deployment, external hosting or execution activation occurred for this implementation.
