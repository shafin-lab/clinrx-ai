# ClinRx Director — ABG and echo combined overview review

Review this four-file downstream increment through PR #23 without a ZIP or Mac access. Production connected execution stays disabled; no merge or deployment is authorized.

## Exact identities

- Source: [131f3413a664b05ad898518f3ce998715d08b53d](https://github.com/shafin-lab/clinrx-ai/tree/131f3413a664b05ad898518f3ce998715d08b53d).
- Tree: `a8f7012d7428de69aefa136d812ed8329b5a75c2`.
- Parent: `6c10b00b2880c5da1e8862144a729a6f914f4298`.
- [Exact diff](https://github.com/shafin-lab/clinrx-ai/compare/6c10b00b2880c5da1e8862144a729a6f914f4298...131f3413a664b05ad898518f3ce998715d08b53d), [complete patch](source.patch), [commit bytes](source-commit.txt), [source/validation identity](source-identity.json), [tested hashes](tested-source.sha256), [four source copies](source/frontend).
- Source/evidence review tags do not change PR #23's draft/open application head `17e2064c3f1a1761876e9a42c5c7a131646d465c`. Its previous CI is not exact-head CI for this increment.

## Change

ABG/blood-gas and echo groups join pressure, flow, rhythm, infusion, fluid and perfusion groups on the existing exact source-time axis. Blood-gas methods only enter the blood-gas group; arterial, central venous and mixed venous sources remain separate. Cells show only their own sample type and FiO2. Missing FiO2 is explicit, never borrowed from arterial samples or inferred as current ventilator settings.

Echo cells preserve raw findings, source production, disclosures and applicable top-level source/acquisition/quality/sample caveats. Source-calculated RVSP/PASP estimates remain labeled. The PH report's lack of invasive confirmation/PAH subtype remains verbatim. Full nested context stays in the inspector; the compact display does not claim to promote every nested caveat. No diagnoses, calculations or clinical confidence scores are added.

Echo remains at 08:00, not carried into later columns. Groups with placeable records elsewhere but none in the selected slice have an explicit message directing users to Earlier times or Show all recorded times. Groups with no placeable records at all are not manufactured; off-axis records remain inspectable. Latest four times remain a source-history slice, not current patient condition. All-time overview has 100 exact source controls; latest slice has 34. Eight groups are available; vertical scrolling is necessary.

Only four frontend files changed. Backend, schemas, fixture data, clinical policies, transport, dependencies, migrations and execution configuration are unchanged. No gate or execution was activated.

## Validation and attribution

- [Final full frontend log](tests.log): 526 tests passed across 14 files, `npm test -- --maxWorkers=2`, exit 0.
- [Final build log](build.log): TypeScript and default Vite build passed, exit 0. Existing bundle-size warning remains.
- Whitespace check passed. Tested-file hashes equal committed bytes. Tests preceded the commit; no clean-archive rerun is claimed.
- Regressions cover sample context/FiO2 separation, original columns and exact source clicks, older echo without carry-forward, source estimate caveats/PH wording, suspect and withdrawn gases, ambiguous gas/echo timing kept off-axis and retained source reachability.
- [Original validation directory](original) is preserved with its original checksum manifest. Its uncommitted/local wording describes the earlier capture. Its changes.patch omits the then-untracked helper; the publication's source.patch includes all four files.
- No new backend suite, hosted CI, explicit hosted-synthetic build or container acceptance is claimed. Existing unexplained parallel-run timeout uncertainty is not resolved by this bounded-concurrency pass.

## Captured evidence

- [Default DOM](browser/default-dom.txt), [all-times DOM](browser/all-times-dom.txt), [ABG screenshot](browser/abg.png), [earlier echo screenshot](browser/echo.png). These were captured before commit from the identical final tested source bytes.
- [Exact pH inspector](browser/abg-inspector-dom.txt) and [exact RVSP inspector](browser/echo-inspector-dom.txt) were captured after commit against the existing real local API. pH fs-PH-60/1 retains 09:00 collection; RVSP m7-RVSP/1 retains 08:00, 45.0 mmHg, source-calculated status and source study/report context.
- [Reference API state](reference-data/state-redacted.json) and [reference gate check](reference-data/checks.json) are COPIED from [prior immutable evidence](https://github.com/shafin-lab/clinrx-ai/tree/bf12f480e5d1200f38de0b016d2ca6e73d88563b/current-data), not fresh exports. The read token remains redacted. New DOM shows the same 156-source coverage and disabled-execution banner. No fresh full database commitment is claimed.
- [Previously verified database bytes, via text chunks](https://github.com/shafin-lab/clinrx-ai/blob/bce7a83cb6bc530ae4d85ff4ca34d2d83ce7a31a/binary-mirrors/expanded-database/index.json) remain available.

Captures are implementer evidence, not a live session witnessed by Director or a complete browser/network trace.

## Prior review boundary

Director accepted F1/F2/database verification at b7d8b806 and the three-group readability increment e7bd733. Preserve those verdicts. Parent 6c10b00 adds BP/MAP, CO and rhythm and remains separately submitted; do not assume acceptance. [Parent handoff](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6222653258) and [parent evidence](https://github.com/shafin-lab/clinrx-ai/blob/7fc416f337229479730fa941881e071c7bec8e90/START-HERE.md) are accessible. Assess applicable parent findings if any.

## Review requested

Recompute publication/source/tested-file identities and verify all 100 exact source/revision/time correspondences. Check all eight groups, sample isolation, estimates versus confirmed findings, original echo timing, empty-slice disclosure, missing/suspect/withdrawn status and off-axis preservation. Inspect raw logs, DOM/screenshots and source. Distinguish independent recomputation from inspected execution results.

[Portable data-only verifier](verify_evidence.py), [manifest](SHA256SUMS.json), [verification output](verification-output.txt). Verifier PASS is implementation-produced, not Director acceptance.

Return a bounded ACCEPTED or CHANGES REQUIRED verdict with exact identities and limitations. Keep production execution disabled; do not merge, deploy, modify the repository or activate gates. No clinical readiness or hosting approval is inferred.
