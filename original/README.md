# Synthetic evidence explanation — local validation

Base: a9e72c507d1e6cf144d928c2ea493651a1482430. This increment is uncommitted local work, separate from Director acceptance of that baseline.

Added a descriptive, source-linked explanation of the blood-sample, cardiac-output/pressure and echo streams. Patient-level relationships remain explicitly unestablished. Unknown quality, contextual/unplaced observations, missing sample context, source estimates and recorded caveats remain visible. No thresholds, derived physiological values, combined scores, diagnoses or treatment recommendations were introduced. HPI remains optional.

Also corrected the RVSP history mock to return matching source identity and signed context, addressing the nonblocking review note.

## Checks

- Full frontend: 461 passed; see frontend.log/json.
- Typecheck, normal build, hosted-mode build and whitespace checks: passed; corresponding logs/json include commands, exit codes and Node version. Builds retain the bundle-size warning.
- Live browser: all three streams displayed; PaCO2 link opened m7-ABG-PACO2 revision 1 with 48.0 mmHg and its arterial sample context; PiCCO uncertainty link opened m7-PICCO-CO revision 1 with unknown quality retained. DOM captures and screenshots are included. Browser error log was empty after the final filename correction.
- All 12 SQLite tables retain their accepted logical row commitment; database-check.json records the check. Execution-disabled banner confirmed in captured DOM.
- No backend, fixture, policy, dependency, migration or production configuration changes. Backend suite was not rerun for this frontend-only increment. No new container or hosted CI acceptance is claimed.

## Earlier attempt

initial-timeout-attempt preserves the first full-run log and exit metadata: 455 passed and 6 failures following approximately 15-minute timer anomalies. The cause was not independently established. The final run completed normally without timeout changes. A case-insensitive module-name collision was separately corrected by giving the component and helper distinct names before the final checks and browser verification.

No push, merge, deployment or production gate activation occurred. The new explanation has not yet received independent Director review.
