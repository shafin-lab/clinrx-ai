# Evidence-entry timeout correction — narrow Director review

Application source: `8c7fedc6db110747966488fbe52bd5815c7c5713`  
Tree: `e7574339576d3167abc356d0bf651b18a55dbfa3`  
Parent: `d5280047f29bc6f089497d02d1c2d7ba14c44c49`

[Source metadata](SOURCE.json) · [One-file diff](original/change.diff) · [Exact tested file](source/evidenceEntry.test.tsx) · [Preserved diagnosis](original/investigation.txt) · [Validation summary](original/validation.json)

## Scope

Exactly one test file changes. The two guided BP/reassessment cases now use accessible role/name queries within the Evidence draft region rather than repeatedly scanning the full page. The 156-record fixture, inputs, component events, assertions and default 5,000 ms timeout remain unchanged. No application/backend/configuration/dependency/fixture or execution-gate change is included.

This is a bounded test correction on parent d528004, not a request to infer acceptance for every intervening downstream feature. Earlier C1/R1/F1/F2 verdicts retain their own source and scope. PR #23 remains draft/open at 17e2064; publication uses separate review tags and does not update its application branch. Its historical CI does not cover this downstream checkpoint.

## Read the evidence in this order

1. [Original isolated reproduction](original/baseline.log): reassessment times out at 6,382 ms; BP passes. [Instrumented repeat](original/profile-before-repeat.log) also fails. The first instrumented run passes and is retained separately.
2. [Per-step measurements](original/profile-before.jsonl) and [temporary profiling test](original/profiling-test.tsx.txt): label queries take 328–792 ms each, corresponding changes 23–31 ms; instrumentation overhead is included. This establishes costly test queries in the reproduced case, not the cause of every historical timeout. Temporary profiling code is not in the application/test candidate.
3. [Final exact-source focused log](original/evidence-entry-final-source.log): **17 passed**, 15.21 s. [Final exact-source full frontend log](original/frontend-final.log): **663 passed across 21 files**, 84.54 s, two workers. [Final typecheck](original/typecheck-final.log): passed. Node24.12.0/npm11.6.2.
4. [Original typecheck failure](original/typecheck.log), intermediate focused log and earlier full-suite log remain distinct. Unsupported role-query `exact` options were removed before final-source checks. The initial 300/486 ms case timings belong to the intermediate focused run; do not relabel them as final-source timings.
5. [Final tested-file hash](original/tested-file.sha256) matches the committed source mirror. Whitespace success is implementation-recorded in validation.json and was checked during publication; no historical raw whitespace transcript is claimed.

Logs are implementation-produced evidence, not Director execution. No new tests were run solely for publication. No fresh browser/API/database observation, build, backend suite, hosted CI, container validation or gate probe is claimed. Production execution configuration is untouched; this is not a new independent observation of the running gate.

## Direct access and verification

All artifacts are ordinary readable text, including JSON/JSONL, logs, source and diff. Nothing requires a ZIP, binary reconstruction or Mac access. Original files, including their checksum manifest, are preserved byte-for-byte under original/; publication wrappers do not rewrite them. Capture-time statements that nothing was pushed remain historical; only this authorized publication supersedes that statement.

[Publication checksums](SHA256SUMS) · [Original manifest](original/SHA256SUMS) · [Artifact index with Git blob IDs](ARTIFACTS.json) · [Data-only verifier](verify_evidence.py)

The verifier uses only Python's standard library, reading local downloaded files and computing hashes/identities. It does not execute the application, tests or profiler. Run `python3 verify_evidence.py` in a downloaded evidence tree, or independently recompute the same values. Source commit/parent raw bytes, exact tested-file hash and blob identities are included for independent inspection.

Production connected execution must remain disabled. No merge, deployment, external hosting or gate activation is authorized or performed. No clinical-readiness claim or new durable browser-session recovery claim follows.
