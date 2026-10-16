# Local synthetic patient-specific interpretation

Base: 33c729d944cf5fd0d6302eb2b19c7e73b697538e. Nine changed/new files are retained as uncommitted local work. No push, merge, deployment, production gate activation or new PR handoff occurred.

The new section separates recorded source assertions, possible clinical meaning and barriers to confirmation. It is an authored explanation of this exact synthetic case, with an explicit unconfirmed combined interpretation. It is not a general diagnostic engine, clinical validation or approved production inference. All new wording awaits independent Director review.

## Validation

- Focused case/integration checks: 47 passed. Initial timestamp-mutation test targeted a nonexistent collected field; corrected to the actual occurred source-time field and rerun successfully. This was test setup, not a demonstrated application failure.
- Full frontend: 484 passed across 11 files; frontend.log/json retain output, command, exit code, runtime version and duration.
- Typecheck, default build, hosted-mode local build and whitespace checks passed; corresponding logs/json retained. Node 22.13.0. Build output retains the nonblocking bundle-size warning.
- Guard regressions cover exact values/units, revision/digest, source time, binding provenance, quality/artifacts, withdrawal, placement, contextual references, disclosures, sample settings, missing/additional/duplicate records, scope/window changes, input ordering and optional unconsumed HPI. Rerender removes stale possibilities immediately.
- Integration checks preserve exact source inspection, read-only browsing, gate-enabled blocking and absence of preparation/execution calls.
- Browser: opened the new section, followed its PaCO2 and RVSP source links to revisions m7-ABG-PACO2/1 (48.0 mmHg with arterial sample context) and m7-RVSP/1 (45.0 mmHg, source-calculated estimate). Saved DOM and screenshots document the presentation. Zero captured browser errors. Execution-disabled banner remains visible in the DOM. These are captures and implementation verification, not independent clinical acceptance or a complete network trace.
- All 12 SQLite tables retain the accepted logical row commitment, 47 fact revisions and two retained receipts. database-check.json records integrity and row commitment.

No backend/model, transport, fixture, policy, production-configuration, dependency or migration file changed. No duplicate backend suite, new exact-head hosted CI or container acceptance is claimed.

Clinical context and exact guard design are documented in docs/SYNTHETIC-CASE-INTERPRETATION.md. The guard ties the authored wording to the full non-HPI fact content and display metadata. It does not authenticate sources independently, assess physiological eligibility or detect updates before a state refresh. The new interpretation does not automatically regenerate on mismatched evidence.
