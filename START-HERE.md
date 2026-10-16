# ClinRx Director — combined overview readability review

Review this six-file downstream increment through PR #23. No ZIP upload or Mac access is required. Production connected execution stays disabled; no merge or deployment is authorized.

## Exact source and relationship to earlier reviews

- Source: [e7bd7337bc61279ca5d14b68fb1f14bed1948121](https://github.com/shafin-lab/clinrx-ai/tree/e7bd7337bc61279ca5d14b68fb1f14bed1948121).
- Tree: `36da03a8de7f1b21b84b65a9f548d9d22bcd1d0b`.
- Parent: `b7d8b806bca6c23d3ab91f3120e36371e78ddc75`.
- [Exact six-file readability diff](https://github.com/shafin-lab/clinrx-ai/compare/b7d8b806bca6c23d3ab91f3120e36371e78ddc75...e7bd7337bc61279ca5d14b68fb1f14bed1948121), [source/parent identity and SHA-256 mapping](source-identity.json), [commit bytes](source-commit.txt), [complete patch](source.patch), [six committed-file copies](original/source).
- [Separate F1/F2 correction re-review handoff](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6222235039). This source inherits those corrections; their independent closure is not assumed. That handoff includes exact prior database bytes in readable base64 chunks.
- PR #23's accepted application head remains `17e2064c3f1a1761876e9a42c5c7a131646d465c`, open/draft and unmerged. Source/evidence review tags do not update its application branch.

## What changed

Combined overview is the default flowsheet view. It shows infusion events, fluid records and perfusion observations together. It includes all recorded infusion instances, interval urine volume, source-reported interval/cumulative chart balance, lactate and capillary refill, using four exact recorded-time columns at a time. Initial display is the final four source timestamps in the bounded state, not a claim about the current patient state.

Earlier/Later controls and Show all recorded times retain every overview event. Entire rows with no records in the selected slice are omitted with visible disclosure; missing cells use dashes explicitly labeled as no record, not zero or continued administration. Other measurements and perfusion observations remain in the detailed sections. All hemodynamic sections retains all 150 plotted source controls and two off-axis records; all 156 bounded-state items remain available in the application.

Compact cells preserve raw quantities/units and explicit order/start/change/pause/restart/stop labels. Quality concerns, missing quality and non-recorded statuses remain visible. Acceptable source quality and full metadata remain in the exact inspector. Infusion identities stay in row labels, including missing identities. Reported balances retain source-calculation qualifiers. Interval bounds shorten only for exact supported same-day UTC source assertions; other context is labeled for inspection. No duration, dose conversion, carry-forward, physiological simultaneity or treatment response is inferred.

Focus chart brings all three groups into view. The detailed reading/ownership caveats remain expandable. This is a presentation increment: backend, demo data, schemas, policy, execution gates, transport, dependencies and migrations are unchanged relative to the parent.

## Final exact-source validation

[Exact commands, source/tree identities, environment additions, exit codes and timings](final-validation/commands.json):

- [Full frontend: 523 passed across 14 files](final-validation/frontend-full.log), using `--maxWorkers=2` from a clean Git archive of e7bd733 with installed pinned dependencies linked.
- [Typecheck](final-validation/typecheck.log), [default build](final-validation/build-default.log) and [explicit hosted-synthetic local build](final-validation/build-hosted.log): exit 0. Existing bundle-size warning remains nonblocking.
- All six increment files match their original captured hashes and committed bytes. No source changes occurred after testing began. No new backend suite, hosted Actions, container or external hosting acceptance is claimed.
- [Original readability validation](original/README.md), logs, captures and manifests remain preserved unchanged under original/. Their historical statements that work was local/uncommitted describe that earlier capture. The original 517-test run predates F1/F2; the new 523-test run validates this integrated source. The initial checkbox layout conflict and final CSS correction remain disclosed.

## Fresh local browser/API evidence

- [Combined overview screenshot](current-browser/combined.png), [complete default DOM](current-browser/combined-dom.txt), [earlier-time DOM](current-browser/earlier-dom.txt), [all overview times](current-browser/all-overview-times-dom.txt), [full chart](current-browser/all-details-dom.txt).
- [Exact compact-cell source inspector](current-browser/source-inspector-dom.txt) and [actual API revision-history result](current-browser/source-history-dom.txt): fs-N-CHANGE/1, 7 mcg/min, exact 70 kg weight reference and separate 5.25 mL/h pump record; inherited F2 mapping labels are visible.
- [Measured layout](current-browser/layout.json): actual 575×823 viewport; document width 575; all three groups fit in the focused chart. This is an observed viewport result, not a universal device/accessibility certification.
- [Fresh redacted API state](current-data/state-redacted.json), [all 12 table row preimages](current-data/all-table-rows.json), [data/gate checks](current-data/checks.json), [live HTTP metadata](current-data/api-metadata.log).

All rows match the prior published synthetic database exports. The unchanged all-table commitment is `273acbe17d027b1836fa893ebb980dcc333fa6d920defdd60f1b4096fbdc02cc` (12 tables, 162 fact revisions, two bootstrap-created retained receipts). The current API reports execution_enabled=false. No database was regenerated. [Exact prior database text-chunk index](https://github.com/shafin-lab/clinrx-ai/blob/bce7a83cb6bc530ae4d85ff4ca34d2d83ce7a31a/binary-mirrors/expanded-database/index.json) remains available for independent binary reconstruction.

Fresh captures were taken from the refreshed local workspace after committing e7bd733, against the unchanged real local API. Earlier captures under original/ predate inherited F1/F2; their inspector text must not be relabeled as new source output. The selected DOM/screenshots and HTTP metadata are not a complete timestamped browser/network action trace. The read token is redacted and cannot be authenticated from the publication. No fresh exact-source external/container exercise or clinical validation is claimed.

## Independent checks requested

Review grouping, page defaults, empty-row omission and recovery, every event's reachability, distinct infusion identities and measurement contexts, raw values/units, unknown/suspect/withdrawn status, source-only balances, conservative interval display, exact inspector/history selection and disabled-execution behavior. Confirm no discarded source record, carry-forward, zero substitution, causal inference or clinical recommendation has been introduced.

[Portable standard-library verifier](verify_evidence.py), [complete checksums](SHA256SUMS.json), [verification output](verification-output.txt). It checks source-file identity, API payload/digest/scope/ingestion correspondence, all-table commitment, 150 detailed controls, 31 all-time overview controls, 14 initially shown controls, selected exact histories and measured layout. These are implementer checks for independent recomputation, not Director acceptance.

Return ACCEPTED for a clearly bounded scope or CHANGES REQUIRED with exact findings. Distinguish inspected logs, independent recomputation and fresh execution. Preserve the separate pending F1/F2 review boundary. **Keep production execution disabled; do not merge, deploy or activate any execution gate.**
