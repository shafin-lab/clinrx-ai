# ClinRx Director — BP/MAP, cardiac output and rhythm overview

Review this four-file presentation increment through PR #23 without a ZIP or Mac access. Keep production connected execution disabled. No merge or deployment is authorized.

## Exact identities

- Source: [6c10b00b2880c5da1e8862144a729a6f914f4298](https://github.com/shafin-lab/clinrx-ai/tree/6c10b00b2880c5da1e8862144a729a6f914f4298).
- Tree: `07c6d28efcfc7398ade23ecd505bef9a0b61a721`.
- Parent: `e7bd7337bc61279ca5d14b68fb1f14bed1948121`.
- [Four-file diff](https://github.com/shafin-lab/clinrx-ai/compare/e7bd7337bc61279ca5d14b68fb1f14bed1948121...6c10b00b2880c5da1e8862144a729a6f914f4298), [complete patch](source.patch), [commit bytes](source-commit.txt), [source hashes](source-identity.json), [tested hashes](tested-source.sha256), [exact source copies](source/frontend).
- PR #23 remains draft/open at `17e2064c3f1a1761876e9a42c5c7a131646d465c`. These separate source/evidence tags do not move the application branch or establish hosted-CI coverage.

## Change and review scope

Combined overview adds systolic/diastolic blood pressure and MAP, CO/CI, and source-reported rhythm/heart rate to existing infusion, fluid and perfusion groups on the same exact source-time axis. CO method/device rows remain distinct; there is no preferred CO, averaging, conversion, generated diagnosis, carry-forward or response inference. The latest four source times remain the initial view, not a current patient-state claim.

All six groups are available in the chart. On the captured narrow viewport, vertical scrolling is required; sticky time headings remain visible. Empty rows in a selected slice are omitted with disclosure. Earlier/later and all-times controls preserve reachability. Full detailed sections and off-axis sources remain available. There are 28 latest-slice controls and 66 all-time overview controls.

Quality and withdrawn/non-recorded status rules and exact inspectors remain unchanged. The 09:00 CO `fs-CO-60/1` retains its suspect label; the inspector preserves 4.60 L/min, bolus thermodilution, SwanGanz/HemoSphere and acquisition context. Raw rhythm wording, including the 08:30 statement that no arrhythmia classification is confirmed, is preserved. Fluid balances remain source assertions over explicit intervals.

Only the four listed frontend files changed. Backend, schemas, fixture data, policies, dependencies, migrations, execution configuration and transport are unchanged. Production execution remains disabled. No new execution was performed.

## Validation

- [Full frontend log](tests.log): 524 passed across 14 files, `npm test -- --maxWorkers=2`, exit 0.
- [Typecheck and build log](build.log): `npm run build` includes TypeScript and Vite, exit 0. Existing bundle-size warning remains.
- `git diff --check`: exit 0. Tests preceded the commit; all four captured tested-file hashes equal the committed source bytes. No separate clean-archive rerun is claimed.
- Tests assert six groups, exact clicks/time columns, source reachability across all pages/all-times, method/device separation, suspect/unknown/withdrawn labels, unchanged input records and contextual CO exclusion from the axis. Existing regression suites include accepted HPI-collision and unit-mapping protections.

No new backend run, hosted CI, explicit hosted-mode build or container acceptance is claimed. Prior parallel-run timeouts remain unexplained; this run used the previously documented two-worker setting without changing timeout thresholds or assertions.

## Browser captures and data boundary

- [Default overview DOM](browser/default-dom.txt), [top screenshot](browser/default.png), [lower chart screenshot](browser/lower.png), [all-time DOM](browser/all-times-dom.txt), [exact CO inspector DOM](browser/co-inspector-dom.txt).
- These are fresh captures of the committed local workspace against the existing real local API. They are not a complete browser/network trace or a live session witnessed by Director.
- [Reference API state](reference-data/state-redacted.json) and [reference gate/data check](reference-data/checks.json) are COPIES from the prior immutable publication, not fresh API exports. Their original source is [bf12f480 current-data](https://github.com/shafin-lab/clinrx-ai/tree/bf12f480e5d1200f38de0b016d2ca6e73d88563b/current-data). Their token remains redacted. The current UI independently displays execution disabled and the same 156-item coverage; no new complete database commitment is claimed here.
- Original database bytes remain [available as exact text chunks](https://github.com/shafin-lab/clinrx-ai/blob/bce7a83cb6bc530ae4d85ff4ca34d2d83ce7a31a/binary-mirrors/expanded-database/index.json). No binary ZIP is needed.

## Prior review boundary

Director closed F1/F2 and database-byte verification at b7d8b806; preserve that acceptance. Parent e7bd733 readability review is separate and not assumed accepted. [Parent review handoff](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6222402342) and [parent complete evidence](https://github.com/shafin-lab/clinrx-ai/blob/bf12f480e5d1200f38de0b016d2ca6e73d88563b/START-HERE.md) remain accessible. If parent review has findings, assess their applicability to this descendant.

## Independent checks requested

Recompute manifest/source/tested-file hashes, inspect all-time/default controls and exact source correspondence, review grouping/time placement/method separation and source-only semantics, and confirm no inference or execution boundary changed. [Portable verifier](verify_evidence.py) and [verification result](verification-output.txt) support independent checking but are implementation-produced.

Return a bounded ACCEPTED or CHANGES REQUIRED verdict identifying exact reviewed source/tree, evidence attribution and limitations. Do not merge, deploy, activate a gate or infer clinical readiness.
