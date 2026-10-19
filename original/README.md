# RF1-F1 correction validation

Candidate: `5cb73212ae6104b02bad361886cd9507795d88bf`
Tree: `7505ff88af8089f2d729fc230b15f3a604c5c9c0`
Parent: `c2d58e4c8d52d2ceeddd57881365cc5f76cdf74f`.

Five-file frontend-only correction. Creatinine history compares the complete selected revision, including fact, digest, canonical payload, ingestion and placement. The RF1 fluid client retains inherited validation and adds exact complete context plus selected fact/ingestion correspondence. Shared hemodynamic history contracts are unchanged. Existing clearing and late-response rejection remain.

14 new targeted cases: three creatinine mutations, unchanged creatinine acceptance, eight fluid contradictions, unchanged fluid plus clearing on failure, and late fluid response rejection. All fluid contradictions first pass the inherited decoder, isolating the RF1 integration guard. Old source: 12 expected failures / 2 controls passed. Corrected focused run: 87 passed across three files.

Final typecheck, default build and explicit RF1 authoring build pass. Existing bundle-size warning remains. Initial typecheck fixture widening failures and the first 35-pass run remain separately retained. Tests/builds preceded the commit against matching final source bytes. No assertion/timeout relaxation.

Hosted CI run 39285512771 was dispatched on the exact candidate. At the last saved snapshot it is queued; both jobs await hosted runner assignment. No hosted success is claimed. No new browser, database, container or independent live execution acceptance is claimed. The running 5197 workspace has not been replaced by this correction. Previously accepted evidence retains original attribution.

Production execution remains disabled. No backend, schema, fixture, dependency, policy, migration, execution configuration or CI workflow change. No merge, deployment or external hosting.
