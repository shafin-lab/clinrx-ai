# Director review: source-linked synthetic evidence explanation

Source **33c729d944cf5fd0d6302eb2b19c7e73b697538e**, tree **39331029fe076c71c17e18cdf72a7f7714b33e50**. Parent independently accepted summary: **a9e72c507d1e6cf144d928c2ea493651a1482430**.

[Exact source](https://github.com/shafin-lab/clinrx-ai/tree/33c729d944cf5fd0d6302eb2b19c7e73b697538e) · [Seven-file incremental diff](https://github.com/shafin-lab/clinrx-ai/compare/a9e72c507d1e6cf144d928c2ea493651a1482430...33c729d944cf5fd0d6302eb2b19c7e73b697538e).

PR #23 remains open/draft at accepted application head `17e2064c3f1a1761876e9a42c5c7a131646d465c`. This is a separate downstream source/evidence review; the PR Files changed tab alone does not contain this increment. Only immutable review tags are published. No application branch is pushed, merged or deployed. Production execution remains disabled.

## Review scope

The patient summary now explains three complementary evidence streams: blood sample/oxygen context, cardiac output/pressures and echo structure/function/estimates. Each stream links its exact source records. Fixed explanatory text is inspectable; case-dependent elements are source records, counts, quality/placement/status flags and preserved caveats. Patient-level relationships remain explicitly unestablished. No new diagnosis, physiological calculation, threshold, preferred CO, time alignment, confidence score, PH/PAH classification or treatment recommendation is generated.

Review preservation of unknown-quality PiCCO, contextual cardiac output, unplaced pressure, missing mixed-venous sample context, echo estimate limitations and source notes. Recorded acceptable quality must not imply confidence in a combined interpretation. Generic view caveats retain every associated source after deduplication. Missing streams must not create findings. HPI remains optional.

The nonblocking RVSP history-test fixture issue from the prior review is corrected: returned history now contains matching RVSP revision 1 and signed context, decoded with the expected reference and scope.

## Directly inspectable evidence

- [Original local report](original/README.md), [seven tested-file hashes](original/tested-source-sha256.json), [committed identity](source-identity.json). All seven committed files match tested bytes.
- [461-test frontend log](original/frontend.log), [command/exit metadata](original/frontend.json), [typecheck](original/typecheck.log), [default build](original/build.log), [hosted-mode local build](original/hosted-build.log), [whitespace check](original/diff.log). Node 22.13.0. Builds retain the nonblocking bundle-size warning.
- [Original explanation DOM](original/explanation-dom.txt), [explanation screenshot](original/explanation.png), [full screenshot](original/explanation-full.png), [flow-source screenshot](original/flow-sources.png), [ABG inspector DOM](original/abg-source-dom.txt), [unknown-quality PiCCO inspector DOM](original/picco-uncertainty-dom.txt).
- [Publication-time expanded DOM](expanded-explanation-dom.txt) exposes all 30 explanation source controls; all 33 original summary controls remain below.
- [SQLite snapshot](synthetic.sqlite3), [12 readable tables](readable-tables.json), [exact row arrays](raw-row-arrays.json), [accepted baseline API state](publication-state.json), [original row check](original/database-check.json).
- [Data-only verifier](verify_evidence.py), [verification output](verification-results.json), [complete file index](INDEX.md), [SHA-256 manifest](SHA256SUMS.json). No ZIP needed.

## Evidence timing and limits

`original/` preserves local validation artifacts unchanged, including their then-true uncommitted/no-push statements. The user subsequently authorized this review publication; it does not authorize application branch publication, merging, deployment or execution activation. Source was committed after testing without changing tested bytes.

The database snapshot and expanded DOM were captured at publication. The API state and readable exports are unchanged copies of the previously accepted summary evidence, not a new API response or new historical snapshot. All 12 current database tables match those exports and the original row commitment `91ed2b1b40f44294d65788ea26deedfd487b2a552d58de9665d0eb366016773c`; all 41 facts/digests/scope/ingestion metadata and two retained receipts match. The API state's read token remains redacted and cannot be signature-authenticated here.

Browser captures show displayed controls, exact source inspection and disabled execution; they are not a complete action/network trace or independent live replay. The verifier reads captured data only and imports no application code. Its PASS is implementation-supplied verification, not Director acceptance. It checks all table exports, source fact/digest/scope/ingestion correspondence, receipt hashes, 30 explanation source identities/values/units/quality/placement, exact ABG and PiCCO inspector content, and check exit metadata.

The [initial full-suite attempt](original/initial-timeout-attempt/frontend.log) is retained separately: 455 passed and six failures accompanied approximately 15-minute timer anomalies; cause was not independently established. Final run passed all 461 tests without timeout changes. A separate macOS case-insensitive module-name collision was corrected before final validation by giving component/helper distinct names.

Backend, models, policies, fixtures, transport schemas, migrations, dependencies and production execution configuration are unchanged. No duplicate backend run, exact-head hosted CI, new container acceptance, external HTTPS or clinical readiness is claimed. The prior Director acceptance applies to the parent, not automatically to this new explanation.

[Previously accepted summary evidence](https://github.com/shafin-lab/clinrx-ai/blob/14d471cc956d31abd60f9aa3bec1d54e2424f06c/START-HERE.md).

Return ACCEPTED for this gated descriptive explanation scope or CHANGES REQUIRED with exact findings and smallest corrections. Distinguish independent inspection, recomputation and execution. Keep production execution disabled; do not merge, deploy or activate gates.
