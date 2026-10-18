# Compact read-only reassessment comparison — local validation

Source: ebbab2955109884169ae7ceef4a87d0f12af4ebf
Tree: 7ecf17aa1918d1267e2e00e91248b039e6632446

Four-file local frontend increment; no backend, schema, clinical policy, fixture or production gate configuration changes. Explicit note A/B selectors use JSON tuple identities; comparison displays exact note identities/revisions, source time, actor/status and retained baseline/intervention/follow-up references. No automatic chronology inference, successor substitution, measurement reloading/calculation, writes or inference execution. Full narrative, uncertainty/provenance and retained records remain expandable. Missing/duplicate/malformed stage metadata or unmatched exact context support withhold the stage reference. Selection persists across reordering; missing selection does not fall back to a new note; foreign encounter notes are excluded. Same-note selection is disclosed.

Validation:
- Focused comparison and existing evidence-entry regressions: 26 passed (8.39s).
- Full frontend: 602 passed across 18 files, --maxWorkers=2, 34.78s. Raw frontend-tests.log retained.
- Final default build/typecheck passed: default-build.log.
- Final local authoring build/typecheck passed: final-authoring-build.log.
- Existing bundle-size warning remains.
- git diff --check passed; working tree clean after local commit.

Initial new-test run failed because of shared test fixture aliasing and unsupported Testing Library query typing; these were corrected before the passing results. The live narrow-viewport check found inherited min-width:720px pushing B off-screen; final CSS sets min-width:0. The full frontend suite preceded that CSS-only correction; final builds and browser checks cover the final CSS. No duplicate full suite was run solely for that style fix.

Browser: existing local 5191 authoring service and database reused. Previous frontend build preserved at guided-entry-local-run/frontend-008034e-before-compact-comparison. Final authoring build installed locally; no external host. Note A abae4ef7-74c4-48cc-bb50-f50e9fb151cd/1 and B 90c89b62-1f3a-4903-b10d-eb8c6711e921/1 were explicitly selected. comparison.txt captures disabled execution, both identities and exact different ABG revisions. comparison.jpg shows the reference table together; full authored text remains collapsed. Recorded viewport 431x823; table top31.84375/bottom809.4375/width365, document width431. This is the exercised viewport only, not general device/touch/accessibility certification.

Actual before/after-view all-table rows compare equal: 174 fact revisions and both retained receipts unchanged. database-preservation.json records data-only result. No new note saved; no independent live reviewer, complete network trace, source-signature authentication, new backend suite, hosted CI or container acceptance claimed. Screenshot/DOM captures preceded the local commit but source.json confirms committed bytes match final files. Durable browser-session recovery remains deferred.

Production execution remains disabled. No push, merge, deployment, external hosting or gate activation. Existing reviewed evidence and earlier accepted scopes are preserved; this new increment is not independently accepted yet.
