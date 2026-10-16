# ClinRx Director — expanded ICU flowsheet review

**Review the downstream source and evidence linked here through PR #23. No ZIP or Mac access is required.** PR #23's accepted application head remains `17e2064c3f1a1761876e9a42c5c7a131646d465c`, open/draft and unmerged. These review tags do not update that PR head or deploy an application.

## Exact source

- [Source cc8aecae112796ef8d086e77f41711a9ed987609](https://github.com/shafin-lab/clinrx-ai/tree/cc8aecae112796ef8d086e77f41711a9ed987609).
- Tree: `b90542937c22d36c841d3692d2c49c5e76487ea1`.
- Parent: accepted descriptive explanation `33c729d944cf5fd0d6302eb2b19c7e73b697538e`.
- [Complete 24-file increment](https://github.com/shafin-lab/clinrx-ai/compare/33c729d944cf5fd0d6302eb2b19c7e73b697538e...cc8aecae112796ef8d086e77f41711a9ed987609), [source identity and SHA-256 file mapping](source-identity.json), [commit bytes](source-commit.txt), [complete patch including new files](source.patch).
- Source tag: `clinrx-icu-flowsheet-cc8aeca`. Evidence tag: `clinrx-icu-flowsheet-evidence-cc8aeca`.

## Scope requiring its own review

This is **not solely a display-only change**. Review the optional `CirculatoryEvent.recorded_interval` contract and generated transport schema as well as fixture, browser and testing changes. Boundaries use existing exact ClinicalInstant admission; omitted intervals preserve old canonical payloads; duration/order are not inferred. Check compatibility and fail-closed behavior rather than inferring approval from earlier M7 or container acceptance.

The 24-file increment also includes the **earlier unreviewed authored exact-case interpretation**. It describes unconfirmed possibilities for the original exact synthetic case. It is not a general reasoning engine and is withheld for the expanded 156-item dataset. Review its exact-evidence guard and confirmation/possibility separation explicitly. Earlier 484-test local evidence is preserved separately in [earlier-case-interpretation](earlier-case-interpretation); it is not substituted for final evidence. No earlier Director acceptance is attributed to this work.

The new flowsheet covers the hemodynamic portions of seven priorities: an integrated recorded-time axis; complete source infusion context; interval fluid/urine/blood/drain/CRRT NET removal context; measurement acquisition context; serial perfusion with distinct ScvO2/SvO2; linked interventions; and source clinician goals/review/handover. See [scope, ownership matrix and international documentation references](original/source/docs/SYNTHETIC-ICU-FLOWSHEET.md). Public Canadian, Australian, historical UK and historical US documentation patterns are examples, not an exhaustive global policy review or adoption of institution-specific targets.

Nutrition, general patient management and comprehensive other-organ workflows remain separate. HPI is optional: 14 of 15 supported families are populated, with HPI absent. VA-ECMO, Impella and IABP remain deferred. No prescribing, dose conversion, forward-fill, causal response classification or production execution is added.

## Evidence navigation

- [Original local validation report and limitations](original/README.md). Its pre-publication statements about uncommitted/unpublished work remain preserved as historical capture status; the source is now committed and review tags published. No merge/deployment/gate activation occurred.
- [Final frontend raw log — 511 passed](original/frontend-quality-final.log), [typecheck](original/typecheck-quality-final.log), [default build](original/build-default-quality-final.log), [explicit hosted-synthetic local build](original/build-hosted-quality-final.log), [commands, environment additions, timing and exit codes](original/frontend-quality-final-results.json).
- [Full backend log — 4,249 passed, one existing warning](original/backend-full.log), [command/exit/timing](original/backend-full-result.json). **This run began before the final four CI fixture records were relabeled source-calculated.** The backend core model/schema remained unchanged; one test was also renamed and given a CI-label assertion.
- [Final corrected-fixture focused backend/API — 33 passed](original/backend-focused-final.log), [command/exit/timing](original/backend-focused-final-result.json). Do not represent the older full run as an exact-final-fixture full run. No new hosted Actions or container acceptance is claimed.
- [Captured full flowsheet DOM](original/flowsheet-dom.txt), [infusion screenshot](original/flowsheet.png), [fluid chart](original/fluid-flowsheet.png), [exact urine inspector](original/urine-inspector-dom.txt), [urine history](original/urine-history-dom.txt), [dobutamine support inspector](original/dobutamine-inspector-dom.txt), [CI acquisition context](original/ci-context-dom.txt), [intervention assessment](original/assessment-dom.txt), [its clicked subsequent CO source](original/assessment-linked-co-dom.txt), [clinician goal](original/goal-dom.txt), [ScvO2](original/scvo2-dom.txt), [SvO2](original/svo2-dom.txt), [suspect CO](original/suspect-co-dom.txt), [summary with old possibilities withheld](original/summary-dom.txt).
- [Captured redacted API state](original/live-state-redacted.json), [index of 156 small readable per-record exports](api-items-index.json). Large JSON files are downloadable using GitHub's Raw action; the small mirrors avoid requiring large-file previews.
- [Final SQLite database](original/synthetic.sqlite3), [all 12 readable table exports](original/readable-tables.json), [raw row preimages](original/raw-row-arrays.json), [released response](original/released_example-response.json), [withheld response](original/withheld_example-response.json), [live checks](original/live-check.json).
- [Original baseline database](original-baseline-database.sqlite3) and [all-table preimages](original-baseline-rows.json), exported read-only at publication time, not new historical before-browser snapshots. All 47 baseline stored fact payloads match the expanded database.
- [Live HTTP metadata](original/live-api.log), [boundary check](original/http-boundary-check.json): only read/history calls during browser inspection; no preparation/execution/reconciliation dispatch; two bootstrap-created receipts remain.
- [Original 88-artifact checksum manifest](original/SHA256SUMS.json), [complete publication checksum manifest](PUBLISHED-SHA256SUMS.json), [portable standard-library data-only verifier](verify_publication.py), [publication verification output](verification-output.txt).

## Review checks and limits

Independently check source identity and file hashes, old event canonical compatibility, exact interval precision, separate units/sample types/infusion identities, orders versus delivery, source-linked weights/pump rates, source-only balances/targets, gaps and off-axis times, unknown/suspect/withdrawn records and missing-reference behavior. Assess whether UI uncertainty and international/module boundaries are truthful. Inspect the authored interpretation separately rather than approving patient-level meaning from chart co-location.

Recompute the assembly digest, all 156 API fact payloads/digests, repository/patient/encounter/cutoff/ingestion correspondence, all-table commitments, original fact retention, retained receipt hashes/content, and plotted source identity/time correspondence. Source revisions and value labels should be inspectable through the published captures and small JSON mirrors. Run supplied checks only if useful; clearly distinguish inspected implementer logs, independent recomputation and fresh execution.

Original row commitment: `91ed2b1b40f44294d65788ea26deedfd487b2a552d58de9665d0eb366016773c`.
Expanded row commitment: `273acbe17d027b1836fa893ebb980dcc333fa6d920defdd60f1b4096fbdc02cc`.
Both include SQLite's sequence table, rowid order and compact sorted-key JSON.

Captured browser states are not a complete timestamped action/network trace or an independent live browser exercise. Keyboard activation was used for off-screen controls; no complete pointer/accessibility audit is claimed. Earlier HMR/selector and fixture-expectation issues remain disclosed in the original report. Bundle size remains a warning. The local build is not a new container build or protected external hosting acceptance. Durable browser recovery remains deferred.

**Production connected execution must remain disabled. No merge, deployment or gate activation is authorized.** Return ACCEPTED for a precisely bounded scope or CHANGES REQUIRED with exact findings, and distinguish clinical readiness from synthetic-demo code/evidence acceptance.
