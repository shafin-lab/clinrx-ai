# C1 re-review — duplicate decoded JSON member names

Corrected source: `db56f7e8164a7a3c46c6c8e17a56c0d9088c2de5`  
Tree: `a60dedfbb8e4f7ecfb82ad8467e3895cde36372b`  
Parent: `ebbab2955109884169ae7ceef4a87d0f12af4ebf`

Review only this three-file C1 correction and its narrow regression evidence. Source is published through tag clinrx-compact-comparison-C1-db56f7e; exact files under source/, raw source commit in SOURCE-COMMIT.txt and diff in correction.diff. PR #23's application branch/head remains 17e2064; its existing CI does not cover this downstream source.

## Correction and assertions

retainedReassessmentReference.ts recognizes a flat object with exactly one decoded kind, id and version, all nonempty strings. JSON.parse is used only on individual string tokens, not the object. Duplicate decoded names are rejected before constructing the reference, including escaped equivalents and identical repeats. Unknown/extra members and malformed grammar fail closed. Ordinary JSON whitespace, member order, valid string escapes and escaped punctuation remain accepted. ReassessmentComparison retains its exact resolved context-association/encounter checks and existing warning. No stored-note repair, historical contract, backend, policy, schema, dependency, migration or gate change.

Start with original/README.md and original/validation.json. They retain exact commands, attributed exit codes, versions, source hashes and limits. All 12 original manifest entries plus the original manifest are unchanged. Capture-time local-only/no-push wording is superseded solely by this source/evidence publication.

- original/old-code-negative-control.log: six expected failures and 26 skipped, using ebbab29 decoder plus the new duplicate-member tests. Conflicting duplicate kind/id/version and escaped equivalent names are reproduced. The tests first demonstrate native last-member-wins parsing into the exact supported reference, then require withholding. This is implementation-produced regression execution, not a newly reproduced API/storage defect or Director's own run.
- original/focused-tests.log: final 49 tests across two files pass, 8.64s, --maxWorkers=2. Includes rendered warnings for all six conflicting cases; identical duplicates; valid formatting/escapes; invalid grammar; existing missing/foreign/mismatched support, tuple collisions, selection behavior and entry/recovery.
- original/default-build.log and original/authoring-build.log: final typecheck/default and authoring builds pass; existing bundle warning remains.
- Initial type-import failures and earlier focused pass are preserved under distinct filenames. They are not substituted for final success.
- Node 24.12.0/npm11.6.2 were used; do not attribute earlier Node22 runs to this correction.

Tests/builds preceded local commit; all three final source hashes match committed bytes. No clean-archive rerun, duplicate full suite, backend suite, hosted CI, browser/API/database exercise, restart or container acceptance is claimed. The corrected authoring build is prepared separately; the running local 5191 workspace was not replaced and remains on ebbab29. No new screenshot is claimed for C1.

## Access, preservation and review boundaries

MIRRORS.json supplies bounded lossless base64 text parts for large/binary artifacts; PUBLICATION-SHA256SUMS.json and verify_publication.py support portable stdlib data-only integrity checks. The verifier does not execute app, tests or supplied logs. No ZIP or Mac access required.

Preserve Director's bounded captured-walkthrough acceptance at dd4e7112a432691683519f1a025be7d2f9fd2821, earlier captured comparison at e1b60bb, saved-note evidence c967cc, R1/F1/F2 closure and other accepted scopes. The old source ebbab29 retains C1; this correction needs its own independent re-review. Earlier evidence remains unchanged, including distinct expansion states: expanded-notes.txt lacked B provenance content, while final.txt established both. No historical capture is rewritten.

Earlier compact UI evidence: https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6252470474
Earlier walkthrough: https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6252522541

Production connected execution remains disabled. No merge, deployment, external hosting or gate activation is authorized or performed. Durable browser-session recovery remains deferred. C1 closure and clinical readiness are not inferred from publication or local checks.
