# PR #23 — guided entry, reassessment and F1/F2 corrections

Source: **fa8ce7dfba52af169c6f474dbd0826d747884945**  
Tree: **cda06aecf68da72b64e998fc446eadbf2881d64e**  
Parent/review baseline: **5e204af79c370bf61e8676b2c6191e5d08cd7d9b**

[Exact application](https://github.com/shafin-lab/clinrx-ai/tree/fa8ce7dfba52af169c6f474dbd0826d747884945) · [Ten-file increment](https://github.com/shafin-lab/clinrx-ai/compare/5e204af79c370bf61e8676b2c6191e5d08cd7d9b...fa8ce7dfba52af169c6f474dbd0826d747884945) · [Workflow/boundaries](https://github.com/shafin-lab/clinrx-ai/blob/fa8ce7dfba52af169c6f474dbd0826d747884945/docs/SYNTHETIC-EVIDENCE-ENTRY.md)

## Review F1/F2 first

- F1: one authoritative source draft; JSON-only, numeric-shortcut and interleaved edits retain the final raw string through preview and submission under existing normalization. No conversion or rounding. See EvidenceEntryWorkspace.tsx, guidedEvidence.ts shortcutValue, and evidenceEntry.test.tsx.
- F2: corrections and withdrawals retain exact calculation_inputs and reviewed upstream dependency edges while adding local actor/source/reason and incomplete-lineage disclosure. Missing/mismatched dependencies remain rejected by existing admission. See evidenceEntry.test.tsx and tests/test_guided_authoring.py.
- Additional hardening: conditional disabled-gate header, blocked new writes on failed confirmation, latest-response refresh guard, exact-revision selection. Pending uncertainty/lookup/explicit retry stays bounded and never silently replaces a draft.

## New guided scope

BP/MAP; ABG/oxygen/lactate; CO/CI; broader echo including LVOT VTI/RVSP/PASP and qualitative findings; distinct infusion orders/preparations/delivery/interruptions; perfusion. One source record/event is appended at a time. Unresolved units and identities, unknown clocks/calibration and source quality remain explicit. HPI/TAPSE are optional. No protected execution or clinical calculation is added.

Reassessment is a clinician-authored descriptive circulatory_event/other, with question, stage-labelled exact baseline/intervention/follow-up references, findings, unconfirmed possibilities, uncertainty and optional next review plan. It is not a generated diagnosis, causal conclusion, responder classification, scheduled task or DynamicAssessment test. Stage references are retained in external_evidence plus exact context associations. No schema/backend application/policy/migration/dependency/Docker change.

## Start with these artifacts

- [Original report](original/README.md), [capture-time validation metadata](original/validation.json), [source hashes / Git blobs](original/source-files.json), [source diff](original/source-diff.patch).
- [65 backend/gateway tests](original/backend.log); [588 exact-head frontend tests](original/frontend-exact-head.log); [32 final focused tests](original/focused-final.log); [normal build](original/default-build-final.log); [authoring build](original/authoring-build-final.log); [typecheck](original/typecheck-final.log). Python 3.11.6 / Node 22.13.0 / npm 10.9.2. No new hosted CI or full backend run claimed.
- [Saved reassessment screenshot](original/reassessment-saved.jpg), [viewport screenshot](original/reassessment-view.jpg), [complete review DOM](original/browser-reassessment-review.txt), [saved DOM](original/browser-reassessment-saved.txt), [selection-form DOM](original/browser-reassessment-form.txt). ABG/CO/echo/infusion/perfusion/MAP review and saved DOMs are named original/browser-*-review.txt and original/browser-*-saved.txt.
- [Before SQLite](original/before.sqlite3), [after SQLite](original/after.sqlite3), [before row bytes export](original/before-rows.json), [after row bytes export](original/after-rows.json), [readable table rows](readable/tables-index.json), [readable state items](readable/state-index.json), [before state, token redacted](redacted/before-state.json), [after state, token redacted](redacted/after-state.json), [local data verification](original/browser-verification.json).

The fresh before checkpoint has 156 assembled items / 162 fact revisions / two retained receipts. Seven explicit browser-guided appends produce 163 items / 169 revisions / the same two receipts. The seven records cover all six requested entry groups and a reassessment linking the exact newly entered CO, infusion and perfusion revisions. Source times/uncertainty remain distinct; the RVSP report stays earlier. The supplied data-only checks compare all original rows and retained receipts, API facts/digests, ingestion correspondence and exact note references. Original before/after snapshots are available here; these are implementation captures, not an independently witnessed live session.

## Integrity and redaction

[Original manifest](original/SHA256SUMS) lists 41 original capture artifacts. **39 manifest-listed originals are published byte-for-byte; the two state responses have their top-level temporary signed state_context replaced only in separate publication copies.** The original manifest itself is also copied unchanged. [REDACTIONS.json](REDACTIONS.json) lists original hashes, published paths and exact semantic changes. Local originals remain intact. Do not claim that the withheld token bytes/signatures are independently authenticated.

[Publication manifest](PUBLICATION-SHA256SUMS.json) covers all published artifacts. [MIRRORS.json](MIRRORS.json) gives bounded base64 parts, lengths, SHA-256 and Git blob identities for all binary/NUL/large artifacts. Concatenating/decoding them reconstructs the exact published bytes, including both original databases and JPEG screenshots, without a ZIP or Mac access. Readable exports supplement the bytes. [Data-only verifier](verify_publication.py) imports no application code; [output](PUBLICATION-VERIFICATION.txt). The local original browser verifier/capture script are preserved for inspection; the publication verifier reads the separately redacted state copies.

## Attribution / limits / publication status

The original README and validation.json record capture-time unpublished status. This GitHub evidence publication supersedes only that status; it does not relabel earlier failures or expand acceptance. Initial backend test table-name errors, the occupied-port attempt and initial typing failures remain disclosed. Prior parallel timeout cause remains unresolved. No duplicate test run was performed just to publish evidence.

Browser DOM/screenshots, request metadata and subsequent API/database snapshots do not constitute a complete browser request/response trace. No new live loss/malformed-response fault injection, restart proof, hosted CI, container validation, signature authentication, clinical validation or Director acceptance is claimed. Actor/source identities are assertions. Exact dosing-weight/pump support and detailed acquisition/calculation inputs still need advanced entry. Pending drafts can be lost on page reload/closure. Guided fields are not reconstructed from an edited normalized JSON draft.

PR #23 remains draft/open/unmerged at **17e2064c3f1a1761876e9a42c5c7a131646d465c**. Its CI does not cover this downstream head. Separate review tags expose source/evidence without modifying its application branch. Previously accepted read-only Docker source d0f94dc remains unchanged. Production connected execution remains disabled. No merge, deployment, external hosting or gate activation.
