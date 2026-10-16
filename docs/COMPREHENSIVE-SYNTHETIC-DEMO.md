# Comprehensive local synthetic demo

This local presentation layers a read-only workspace over the existing scoped M7 APIs. It includes 26 recorded items across all 15 evidence families, cardiac output/index, echo TAPSE/LV EF/LVOT VTI, ECG/rhythm, PAC/RHC, FloTrac/HemoSphere, PiCCO and VolumeView/EV1000 source assertions. These are fabricated records, not device connections, validated device capabilities, patient-care data or clinical advice. Source unit mapping remains visible; no unit conversion or derived hemodynamic calculator is added.

## Run locally

From the repository root, with the pinned backend environment and installed frontend dependencies:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python tools/run_comprehensive_demo.py
```

Default UI: `http://127.0.0.1:5179`; API: `http://127.0.0.1:8766`. The launcher refuses occupied ports and existing database files. Optional arguments are `--directory /absolute/new/path`, `--api-port PORT`, and `--web-port PORT`. Both services bind only to loopback. The launcher creates a fresh disposable directory, prints its location, and verifies the real state endpoint reports `execution_enabled=false`. It keeps signing keys in process environment only and does not modify `.env` files or deployment configuration. Ctrl+C stops its two child servers; the fabricated database/logs remain for inspection.

Bootstrap alone, for inspection without starting servers:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python -m app.demo.comprehensive --database /absolute/new/disposable.sqlite3
```

API startup never seeds this dataset automatically. Existing databases are not reset or overwritten.

## Try these journeys

1. **Patient overview → Cardiac output + echo:** compare exact recorded values and source methods. Inspect cardiac output, LV EF or VTI to reveal quality, unit-mapping status, source time and complete provenance. Featured cards are fixture presentation choices, not clinical rankings.
2. **Evidence library:** browse all 15 families; search FloTrac, PiCCO, an exact source ID or a measurement. Contextual and unplaced records remain visible and labelled; a missing family or search match never establishes clinical absence.
3. **Follow a correction:** inspect monitoring configuration `m7-CAL/2` and its bounded history. Revision 2 changes provenance only; the original revision remains available.
4. **Find the evidence gaps:** inspect unknown-quality PiCCO output, earlier contextual output, an unplaced pressure record and unavailable waveform samples.
5. **Recording timeline:** browse repository ingestion sequence. Exact source time and ingestion time remain distinct; this is not acquisition-time sorting or a new temporal inference. Open revision history to inspect corrections at the current cutoff.
6. **Retained examples:** open the released example and the withheld example. Inspect original P/L/V plus CAL/1 evidence, final support witnesses and complete governance receipts.

The older patient, microbiology and protected-review interfaces remain available at `?workspace=legacy`. Navigating there is a normal page navigation, not a hidden component replacement; existing unresolved-command unload protection remains in its original interface.

## Execution boundary

The main demo screen uses state, history and retained-lookup operations only. It has no prepare/execute control and does not call those methods. New connected M7 execution stays disabled in the actual API configuration; production configuration and environment loading are unchanged.

During explicit **offline disposable fixture bootstrap only**, the protected workflow creates two real retained examples before the server starts. The first releases unchanged selected evidence. The second is prepared before a calibration-support provenance correction and then withholds after that correction. Both retain exact original CAL/1 evidence; current state shows CAL/2. Their fixed UUIDs are `00000000-0000-4000-8000-00000000c901` and `00000000-0000-4000-8000-00000000c902`. They belong to the new disposable repository, not to production or the prior acceptance evidence databases. Reading them does not authorize or trigger new execution.

No clinical policy, inference eligibility, Kernel/M5/M6/H1-D workflow, schema, migration or dependency changes are made. The demo is a new local branch derived from the accepted PR #23 application head `17e2064c3f1a1761876e9a42c5c7a131646d465c`; it is not part of that independently accepted tree. Independent review of these new demo changes remains separate. Nothing is pushed, merged or deployed by the launcher.

Durable browser-session command recovery remains deferred. The new read-only workspace does not retain an execution command; the legacy interface still has its documented reload/closure limitation. No clinical validation or production activation is implied.

## Checks

`tests/test_comprehensive_demo.py` exercises full-family data, device/method assertions, closed-gate API rejection without writes, exact retained release/withhold, support correction history and refusal to overwrite a database. `frontend/tests/comprehensiveDemo.test.tsx` exercises useful overview/browsing, uncertainty visibility, exact source/history requests, late-response isolation, retained lookup failure clearing, source lexemes, read-only behavior and failed loading without invented data. Browser acceptance additionally covers the actual local API and responsive layout. Record exact commands/results in the local validation report; passing tests alone do not authorize merge or deployment.
