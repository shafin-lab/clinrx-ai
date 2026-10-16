# ClinRx Director — F1/F2 corrections and lossless binary evidence supplement

This supplement is linked through existing PR #23. No ZIP, Mac access, merge or deployment is required. Production connected execution remains disabled.

## Exact correction source

- Source: [b7d8b806bca6c23d3ab91f3120e36371e78ddc75](https://github.com/shafin-lab/clinrx-ai/tree/b7d8b806bca6c23d3ab91f3120e36371e78ddc75).
- Tree: `94f4cdd6a824f1afe2c641e9e56a260df4f509b8`.
- Reviewed baseline: `cc8aecae112796ef8d086e77f41711a9ed987609`.
- F1 commit: `aead3e941201a44d92ff2e81e45c517a708ee0b8`.
- F2 commit: `b7d8b806bca6c23d3ab91f3120e36371e78ddc75`.
- [Eight-file correction diff](https://github.com/shafin-lab/clinrx-ai/compare/cc8aecae112796ef8d086e77f41711a9ed987609...b7d8b806bca6c23d3ab91f3120e36371e78ddc75), [source identity](source-identity.json), [full patch](source.patch), [eight SHA-256 source identities](source-sha256.json), [exact committed file copies](source).

The newer six-file Combined overview readability increment stays **local, uncommitted and excluded** from this source and its validation. The clean Git export used for tests contains the older reviewed flowsheet plus only these eight correction files. PR #23's application head remains `17e2064c3f1a1761876e9a42c5c7a131646d465c`, open/draft and unmerged; only source/evidence review tags are published.

## F1 — optional HPI collision

Narrative rendering now receives a resolver only after the existing complete non-HPI exact-case guard matches. Its input map contains matched non-HPI records keyed by full kind/ID/revision. Narrative source labels resolve through immutable authoring pins to those full keys. HPI cannot enter or override the map, and the pH sample context uses the same pinned resolver.

The [fixture generator](source/tools/export_hpi_collision_fixture.py) persists a genuine typed `circulatory_device_prediction` HPI fact with ID `m7-ABG-PH` alongside the unchanged original oxygen fact, then retrieves the 42-item state through the actual gated API. The two input-order permutations retain valid repository/cutoff/ingestion/coverage data and recomputed assembly digests; their read tokens are unusable fixture placeholders. This is not an oxygen record relabeled as HPI.

[Regressions](source/frontend/tests/caseInterpretation.test.tsx) decode both permutations and assert unchanged pH value, arterial/FiO2 context, displayed possibilities, and exact original oxygen item on click. Existing change/withdrawal/missing/duplicate/foreign-scope tests remain; the expanded-dataset withholding regression remains in the comprehensive suite.

[Old-code negative control](validation/f1-old-code-negative-control.log): the new collision tests ran in an isolated copy with exactly the two F1 source files restored from cc8aeca. One input order passed and the HPI-last order failed; 21 unrelated tests were excluded. Corrected source was restored and hash-checked before final testing. The user's live workspace was not reverted.

## F2 — actual quantity mapping status

[Mapping resolver](source/frontend/src/demo/sourceUnitMappings.ts) reports result quantity, event amount, prescribed/delivered/prepared rate and concentration separately when supplied. The inspector displays each quantity's raw unit and actual source mapping status; it no longer labels an event amount or rate's recorded unresolved mapping as absent/not applicable. No mapping is inferred or normalized.

[Regressions](source/frontend/tests/sourceUnitMappings.test.tsx) check actual displayed urine amount, prescribed dobutamine rate and delivered rate, plus separate concentration and no-quantity cases. These are read-only UI tests and assert no prepare/execute call.

## Validation and attribution

See [validation report](VALIDATION.md), [all exact commands and initial outcomes](validation/commands.json), [controlled-concurrency commands](validation/bounded-commands.json) and raw logs. The source was exported from the final commit into an isolated directory; the installed pinned frontend dependencies were linked without changing dependency files. Tests did not use the local uncommitted Combined overview.

The initial full parallel run had **514 passed and three 5-second timeouts**, including one existing circulatory test and two new inspector tests. Its log is retained unchanged. This is not relabeled as a proven environmental cause or hidden by the passing focused tests. The unchanged source was then tested with fewer concurrent workers; no test assertion or timeout threshold was weakened. Results and remaining limits are stated in VALIDATION.md.

Backend models, clinical policies, fixture seeding for the demo, API transport, execution services/gates, dependencies, migrations and production configuration are unchanged by these corrections. The new tool only generates a frontend regression fixture explicitly. No backend full-suite, new hosted CI, container run or fresh exact-head browser exercise is claimed.

## Database-byte gap — exact existing bytes, not a regenerated database

[Expanded database text-chunk index](binary-mirrors/expanded-database/index.json). Each chunk is a small GitHub-readable base64 text file listed in order. Strip only terminal newlines, concatenate the base64 text in index order, and decode. The included [standard-library verifier](verify_binary_mirrors.py) does this, checks every chunk's SHA-256 and exact reconstructed size/digest, opens the reconstruction read-only, checks SQLite integrity and compares all 12 tables to the original exports.

- Original artifact: `original/synthetic.sqlite3` from evidence `48d5383af61cc56358a31c53200ea4328975d515`.
- Exact bytes: **1,114,112**, in **23** text chunks.
- Original SHA-256 preserved: `4c363b40e716d1f8d5b858d9a7fd7f24b2ee8a8c578afadfe1020a3800920f98`.
- Original all-table commitment: `273acbe17d027b1836fa893ebb980dcc333fa6d920defdd60f1b4096fbdc02cc`.
- Original [raw row arrays](database-reference/raw-row-arrays.json), [readable tables](database-reference/readable-tables.json) and [redacted captured API state](database-reference/live-state-redacted.json) are copied byte-for-byte for comparison.
- [Reconstruction verification output](binary-verification.json): integrity OK, 12 tables, 162 fact revisions, two retained receipts, exact export equality.

The optional previously inaccessible [earlier full screenshot](binary-mirrors/earlier-full-screenshot/index.json) is also mirrored in 24 chunks, preserving its **1,136,090 bytes** and SHA-256 `e78518d4e0d60f48d902dd920b2b02a44369e4c26bc899044e004632dcfdbc63`. Its original `.png` filename actually contains JPEG bytes; the mirror preserves the bytes and documents that fact rather than converting the image.

Run `python3 verify_evidence.py` on a downloaded readable evidence tree for publication/source/fixture checks and lossless reconstruction. It imports no application code and requires no credentials. The [SHA-256 manifest](SHA256SUMS.json) covers all supplied artifacts. These are implementation checks for independent recomputation, not a Director verdict.

The older `ci-context-dom.txt` from prior evidence shows quality count 2; later captures show the final count 5. It remains an older iteration capture, not a final-state screenshot. This supplement does not relabel those mixed captures, authenticate the redacted read token, or turn selected screenshots into a complete browser/network trace.

## Requested re-review

Check F1 exact pinned resolution and genuine HPI collision cases; F2 actual quantity/status labels; correction source/test identity; reconstructed binary checksums/integrity/export equality; and validation attribution. Return ACCEPTED for the precisely reviewed synthetic scope or CHANGES REQUIRED with exact findings. Preserve prior bounded positive findings without extending acceptance to unreviewed local readability changes.

**Production execution must remain disabled. No merge, deployment, clinical-readiness approval or gate activation is authorized.**
