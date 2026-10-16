# Director review: combined synthetic patient summary

## Exact source

- Source commit: **a9e72c507d1e6cf144d928c2ea493651a1482430**
- Source tree: **ba7eccdd4b337e4696d1d4d552f384ddd36688e1**
- Parent ABG/echo source: **66725cf1d51064a7d7956aa503f897cf920057ca**
- [Source](https://github.com/shafin-lab/clinrx-ai/tree/a9e72c507d1e6cf144d928c2ea493651a1482430) · [Four-file incremental diff](https://github.com/shafin-lab/clinrx-ai/compare/66725cf1d51064a7d7956aa503f897cf920057ca...a9e72c507d1e6cf144d928c2ea493651a1482430)
- PR #23 remains draft/open at accepted application head `17e2064c3f1a1761876e9a42c5c7a131646d465c`.

This is a separate downstream source/evidence review. Inspect these linked
checkpoints rather than only the PR Files changed tab. Prior ABG/echo acceptance
does not cover this new summary or its display correction automatically.
Production connected execution stays disabled. No merge, deployment or gate
activation is performed or authorized. Only review references are published;
no application branch is pushed.

## New scope

Patient summary brings 33 source records from a 41-record bounded patient state
into four sections: ABG/oxygen transport; cardiac output/pressures; echo/right-heart
findings; perfusion/circulatory support. The other eight records remain in the
Evidence library. All 15 supported families remain available; 14 are populated
because HPI is optional and absent in this synthetic case.

Source values, units, revisions, methods, quality, status, times, contextual and
unplaced labels remain visible. All summary source buttons open the existing
inspector and cutoff-bounded history using the exact reference. Sample settings
are read from each source only, never copied across samples. There is no preferred
cardiac-output value, averaging, inferred simultaneity, integrated score,
acid-base interpretation, new PH/PAH diagnosis or treatment recommendation.

The qualitative-echo wording issue from the prior review is corrected: the
inspector calls the preserved raw field **Recorded production tag** and explains
that qualitative echo findings are source-report assertions, not directly measured
diagnoses. A focused m7-PH regression covers this presentation boundary. No model,
production enum or policy changes were introduced.

## Accessible evidence

- [Original local report](original/README.md), [tested-file SHA-256 values](original/source-identity.json)
- [453-test frontend log](original/frontend.log), [command/exit code](original/frontend.json)
- [Typecheck](original/typecheck.log), [default build](original/build.log), [hosted-mode local build](original/hosted-build.log), [whitespace check](original/diff.log)
- [Captured summary DOM](original/summary-dom.txt), [complete summary screenshot](original/summary-full.png), [original live check](original/live-check.json)
- [Publication-time API state](publication-state.json), [consistent SQLite snapshot](synthetic.sqlite3), [12 readable table exports](readable-tables.json), [exact row-array preimages](raw-row-arrays.json), [API path logs](runtime-api.log)
- [Portable data-only verifier](verify_evidence.py), [verification output](verification-results.json), [complete index](INDEX.md), [SHA-256 manifest](SHA256SUMS.json)

The four tested source files were checked before and after source commit creation;
the commit contains exactly the tested bytes. Runtime: Node 22.13.0; the full
frontend suite, typecheck and both local build modes exited 0. These local build
artifacts were not deployed. Backend/model, transport schemas, data fixture,
execution policy/configuration, migrations and dependencies are unchanged from
66725cf. No duplicate full backend rerun or new hosted CI/container run is claimed.

Underlying ABG/echo data and prior 4,245-backend-test evidence remain available at
[the previous handoff](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6216974038) and
[the prior immutable evidence guide](https://github.com/shafin-lab/clinrx-ai/blob/81ed2f3051d207834f2636345e5e1879922c727e/START-HERE.md).

## Independent inspection without Mac access or ZIP

Download individual files using GitHub Raw/API, or fetch the evidence tag into a
Git checkout. Run `python3 verify_evidence.py` if desired. The verifier uses only
Python standard-library read operations and SQLite read-only mode; it imports no
application code, executes no captured script and contacts no network endpoint.
It writes its deterministic verification-results.json beside the evidence.

It verifies the manifest, original manifest, all 12 table exports, all 41 API
facts/content digests, patient/encounter and repository/cutoff/ingestion identities,
the 33 unique captured summary source IDs/revisions and their value/unit/quality/
placement text, plus stored receipt hashes and the unchanged row commitment.
Use independent assertions as appropriate; a supplied verifier is not independent
acceptance by itself.

## Evidence timing and honest limits

`original/` preserves the captures and logs unmodified, including their then-true
uncommitted status. Source was committed later without changing any tested file.
The SQLite snapshot, table exports, API state and portable verifier are added at
publication time. Their row digest matches the original summary live check and
prior ABG/echo commitments. They are not independently captured before/after
snapshots of every browser action.

The original browser report describes opening an ABG source/history and the PH
inspector. The saved DOM shows the summary and corrected PH inspector; it is not
a complete action/network trace for those interactions. API path logs and source/
component regressions provide supporting evidence, not a replacement live replay.
The publication API state is a later response, with its signed read context
replaced by an unusable placeholder; original signature verification is not
possible from it. All data is fabricated. No credentials, signing keys or
unrelated local files are included. The local server logs are publication-time
copies. External HTTPS, visitor access, clinical readiness and new independent
live-browser execution are not claimed.

Please return ACCEPTED for this gated synthetic-summary scope or CHANGES REQUIRED
with precise findings/reproduction steps. State what was independently inspected,
recomputed or executed. Keep production execution disabled; do not merge, deploy
or activate execution.
