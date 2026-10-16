# ABG and echo in combined overview

Local uncommitted increment over 6c10b00b2880c5da1e8862144a729a6f914f4298. Four changed/new frontend files; no push, merge or deployment.

Added blood-gas and echo groups to the same exact-source-time overview. Sample type and each sample's own FiO2 remain visible, including missing FiO2 for venous samples; context is never borrowed. Source production and top-level source/acquisition/quality/sample caveats are shown, with complete nested source context retained in the inspector. Reported PH wording is not transformed into a diagnosis.

Groups with placeable historical records but no records in the selected slice have an explicit empty-slice message. Echo findings stay at 08:00; no carry-forward to later times. Existing placement, values, raw units, source selection, quality/status and time navigation remain.

Final validation (17 October 2026, Asia/Kolkata):
- npm test -- --maxWorkers=2: 526 tests passed, 14 files.
- npm run build: TypeScript and Vite passed; existing bundle-size warning.
- git diff --check: passed.
- Real local browser/API: 156 source items, 34 latest controls, 100 all-time overview controls; exact pH fs-PH-60/1 and RVSP m7-RVSP/1 inspectors checked. The execution-disabled banner remains visible. Fresh DOM/screenshots saved here.

New regressions cover original source columns, no echo carry-forward, exact inspector selection, source-calculated estimate caveats, distinct central/mixed venous samples without arterial FiO2 substitution, suspect/withdrawn gas findings and ambiguous gas/echo times kept off-axis. Source snapshots/hashes capture final tested bytes.

Backend, fixture data, schemas, policies, dependencies, migrations, transport and gate configuration are unchanged. No new backend, hosted-CI, hosted-mode build or container acceptance is claimed. Director review of this increment is pending.
