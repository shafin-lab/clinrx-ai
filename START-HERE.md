# RF1-F1 focused correction and hosted CI review

Application: `5cb73212ae6104b02bad361886cd9507795d88bf`  
Tree: `7505ff88af8089f2d729fc230b15f3a604c5c9c0`  
Parent: `c2d58e4c8d52d2ceeddd57881365cc5f76cdf74f`  
Approved specification: `7fa529dd276ceb140700760a358cf3493b44e85b`.

Review the [five-file source diff](original/source.diff), [exact tested-source correspondence](source-correspondence.json), [final results](FINAL-RESULTS.json) and [hosted CI run](https://github.com/shafin-lab/clinrx-ai/actions/runs/39285512771) as one focused RF1-F1 re-review. Specification approval and earlier normal-flow evidence do not themselves close this code finding.

## Correction

Creatinine history validation receives the selected composite observation and requires complete selected-revision equality: fact, canonical payload, expected digest, ingestion and placement. The existing context, chain, scope, canonical and digest checks remain.

The RF1 fluid-history method retains inherited circulatory decoding, then checks the complete original composite context: transport version, assembly request (repository/cutoff/window/profile/limits) and assembly digest, plus exact selected fact and ingestion correspondence. The shared circulatory decoder and other hemodynamic history paths are unchanged. The RF1 panel uses this guarded method. Existing clearing on new selection/failure and generation-based late-response rejection remain.

No backend, schema, fixture, policy, dependency, migration, CI workflow or execution-configuration change. Backend and backend-test trees equal the parent. This package changes no application source.

## Regression and local validation

Fourteen new cases cover three creatinine contradictions (including a changed value with recomputed canonical/digest), unchanged creatinine history, eight fluid contradictions, unchanged fluid history followed by failure/clearing, and late fluid response rejection. The eight fluid mutations explicitly pass the inherited decoder before the RF1 boundary rejects them, isolating this integration gap. The tests use real clients/decoders with mocked HTTP transport and component rendering, not live hostile backend/browser responses.

Old source with the new tests: 12 failures and two passing controls. Three creatinine failures resolved instead of rejecting; eight fluid contradictions and the second invalid lookup failed withholding/warning assertions. The valid-history and late-response controls passed. Final correction: **87 focused tests / three files passed in 12.15s**, including existing circulatory regressions. Final typecheck, default and explicit RF1-authoring builds passed. No assertion or timeout thresholds were relaxed.

[Original logs and exact commands](original/commands.json) remain byte-preserved. The first corrected focused run passed 35 tests; initial typecheck failed because raw JSON fixture types widened `fact.kind`. The test setup was corrected to use decoded typed observations; final typecheck passed. The old-code control preceded that test-typing setup correction. Tests/builds preceded the commit against matching final file bytes; no clean-archive rerun is claimed. Existing bundle-size warnings remain.

## Exact-candidate hosted CI

Run **39285512771**, attempt 1: **SUCCESS**. Both actual job checkout logs identify **5cb73212ae6104b02bad361886cd9507795d88bf itself** via `workflow_dispatch` on tag `clinrx-rf1-f1-5cb7321`; this is neither PR #23's older head nor a synthetic merge checkout.

- [Backend raw log](hosted/backend.log): **4,318 passed**, one existing Starlette/httpx warning, **1,093.79s**; Python 3.11.6, dependency consistency and `m7_0008` passed.
- [Frontend raw log](hosted/frontend.log): **710 passed / 23 files**, typecheck, default build and synthetic-authoring build passed; Node 22.13.0 / npm 10.9.2.
- [Run and job metadata](hosted/run.json); [exact source workflow](hosted/workflow-at-source.yml).

Hosted authoring sets `VITE_SYNTHETIC_HOSTED=true` and `VITE_SYNTHETIC_AUTHORING=true`; it does not explicitly set RF1. The separate local build additionally sets `VITE_SYNTHETIC_RF1=true` and passed. Local Node 24.12.0/npm 11.6.2 results are distinct from hosted Node 22 results.

The earlier queued status in original/README.md, original/commands.json and original/hosted-CI-status.json is retained as the earlier observed status. This new successful run metadata/log evidence supersedes that status; originals are not rewritten.

## Integrity and readable access

[Publication checksums](PUBLICATION-SHA256SUMS.json), [original checksums](original/SHA256SUMS.json) and [lossless text mirrors](MIRRORS.json) support direct inspection without a ZIP or Mac access. Larger text logs/diffs have exact UTF-8 chunk mirrors (concatenate bytes in manifest order) as well as their unchanged original files. [verify_publication.py](verify_publication.py) performs data-only checks: checksums, mirrors, source commit/blob identities, source hashes, unchanged backend trees and captured CI identity/totals. It does not execute the application or tests.

## Attribution and remaining boundaries

The original RF1 evidence remains at `0c4ec5623d9405c4e1547ba39601596861654879` and retains its normal-flow/database/browser attribution to c2d58e4. It is not relabelled as a new corrected-source browser exercise. This supplement adds correction/tests and successful exact-candidate hosted CI, not new API/database checkpoints, live adversarial browser exercise, container validation, independent uncoached usability or clinical validation. The local running workspace was not updated in this publication.

Preserve approved RF1 scope, all six specification conditions and earlier hemodynamics/M1/C1/R1/F1/F2 acceptances. Ask Director for one focused RF1-F1 closure verdict, not duplicate broad tests solely for republication. The separately recovered M1–M18 roadmap remains documentation-only and does not approve this implementation.

Production execution stays disabled. PR #23 remains draft/open/unmerged at unchanged head `17e2064c3f1a1761876e9a42c5c7a131646d465c`. Source and evidence use review tags without updating its application branch. No merge, deployment, external hosting or gate activation.
