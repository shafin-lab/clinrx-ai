# PR #23 — guided walkthrough supplement and narrow R1 correction

Two scopes are deliberately separate. The captured walkthrough ran the **previous application fa8ce7d**; the **R1 correction is new source 008034e**. The walkthrough is not a new browser exercise of the corrected source.

## Identities and review status

- Corrected source: **008034ea12275406d8f5aede8ceb3aa5142570b6**
- Corrected tree: **f9e626c1e4f3a478644a079cba9cf1437c04b2d7**
- Parent and walkthrough application: **fa8ce7dfba52af169c6f474dbd0826d747884945**
- Parent tree: **cda06aecf68da72b64e998fc446eadbf2881d64e**
- Prior application evidence: **62cc60ab37d03fb978e4e0a9dad5226b764f88a5**

[Corrected source](https://github.com/shafin-lab/clinrx-ai/tree/008034ea12275406d8f5aede8ceb3aa5142570b6) · [Nine-file correction increment](https://github.com/shafin-lab/clinrx-ai/compare/fa8ce7dfba52af169c6f474dbd0826d747884945...008034ea12275406d8f5aede8ceb3aa5142570b6) · [Prior evidence guide](https://github.com/shafin-lab/clinrx-ai/blob/62cc60ab37d03fb978e4e0a9dad5226b764f88a5/START-HERE.md)

The user supplied Director's verdict closing F1/F2 and accepting guided source entry within its local synthetic prototype scope. Reassessment remained changes-required for R1. This publication requests narrow R1 re-review and bounded walkthrough-evidence inspection; it does not claim Director has accepted the correction.

## A. Original guided walkthrough — fa8ce7d

All nine original captures/exports are copied byte-for-byte, with [original hashes](WALKTHROUGH-ORIGINAL-SHA256SUMS.json):

- [ABG form](walkthrough/original/abg-form.txt), [validated ABG review](walkthrough/original/abg-review.txt), [saved ABG](walkthrough/original/abg-saved.txt).
- [Reassessment form/selections](walkthrough/original/reassessment-form.txt), [review](walkthrough/original/reassessment-review.txt), [saved note](walkthrough/original/reassessment-saved.txt), [actual saved viewport JPEG](walkthrough/original/saved-reassessment.jpg).
- [Stored new records and payload hashes](walkthrough/original/stored-records.json), [original local verification summary](walkthrough/original/verification.json).

The example adds arterial pH **7.3300** at **09:45 UTC**, specimen walkthrough-arterial-0945, its own FiO2 **40%** and PEEP **5 cmH2O**, with unknown source quality/clock. It saves at ingestion **170**. The clinician-authored fictional reassessment saves at **171**, linking:

- Baseline: circulatory_oxygen / a02f88e1-db04-48a0-89e6-f236016a38a8 / 1 (earlier pH 7.3400).
- Intervention: circulatory_vasoactive / 99a26724-026c-4ccc-ac63-c22ddada2664 / 1 (documented dobutamine change).
- Follow-up: circulatory_oxygen / 1c1f16d9-33d7-40fb-a94f-013a383c9bfc / 1 (new pH 7.3300).

Recorded findings, unconfirmed possibilities, gaps and a review plan remain separate. No treatment effect, diagnosis, calculated response or scheduled action is established. These IDs do not exercise R1's slash collision; this successful capture cannot close R1.

### Publication-time database support

[SQLite bytes](walkthrough/publication-checkpoint.sqlite3), [all 12 table exports](walkthrough/publication-tables.json), [readable individual rows](readable/TABLES-INDEX.json), [169-row comparison baseline](walkthrough/baseline-169-rows.json).

The SQLite export was taken **later, read-only, during publication preparation**, not during the browser walkthrough. It matches the two stored record identities/hashes and 171 total fact rows. All prior 169 rows and both receipt rows match the preserved baseline exactly; all other tables remain equal except the expected sequence counter. The baseline is a byte-identical copy of original/after-rows.json in prior evidence 62cc60ab. This is a later matching export, not a newly captured historical before/after pair. No browser rerun or API response was generated for this supplement.

## B. R1 correction — 008034e

[Source file hashes/Git blobs](correction/SOURCE-FILES.json), [source diff](correction/SOURCE-DIFF.patch), [validation metadata](VALIDATION.json).

- evidenceIdentity.ts encodes [kind, id, revision] as a JSON tuple. Resolution parses the tuple, checks its shape/types and matches each component exactly. Malformed, missing and legacy delimiter strings do not silently resolve.
- GuidedEvidenceForm uses these tuple values and keys for all three stage selectors; EvidenceEntryWorkspace uses the same key for source rows. No historical ID/revision restriction or persisted contract change.
- Four valid fixtures include the exact pressure collision a/b + c versus a + b/c, plus an analogous intervention-event collision. The real API test validates, saves and looks up all four unchanged and confirms no original/receipt changes.
- UI regressions select each pressure and intervention record in both array orders. They assert distinct menu values and exact preview/submitted stage references, narrative and associations. Missing-reference and wrong-intervention rejection remain covered.
- A focused test reproduces the old delimiter collision and wrong-first-item resolution as a negative comparison; this is not a claim of a full old-application browser run.
- The nonblocking F1 test improvement reacquires the mounted textarea, checks intermediate shortcut value 7.37 and preservation of unrelated fields before final JSON edit/submission 7.38. F1/F2 implementation is otherwise preserved.

### Narrow checks (implementation-produced, not Director reruns)

- [37 focused frontend tests](correction/focused.log): npm test -- --maxWorkers=2 tests/evidenceEntry.test.tsx tests/guidedEvidence.test.ts; 8.36 seconds, passed.
- [15 guided backend/API/storage tests](correction/backend.log): PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 backend/venv/bin/python -m pytest tests/test_guided_authoring.py -q; 40.72 seconds, passed, one existing Starlette/httpx warning. These include genuine admission/storage of the collision fixtures.
- [Default build/typecheck](correction/default-build.log): VITE_SYNTHETIC_HOSTED=false VITE_SYNTHETIC_AUTHORING=false npm run build; passed.
- [Authoring build/typecheck](correction/authoring-build.log): VITE_SYNTHETIC_HOSTED=true VITE_SYNTHETIC_AUTHORING=true npm run build -- --outDir <local-validation>/authoring-build; passed. The build output was kept local and is not published as a hosted app.
- Whitespace checks passed. Python 3.11.6; Node 22.13.0; npm 10.9.2. Tests/builds preceded the commit against the same committed source bytes.

No new full frontend/full backend suite, hosted CI, container validation or live corrected-source browser exercise is claimed. The prior 588-test result belongs to fa8ce7d and is not substituted for this correction's focused checks. Prior timeout uncertainty and all earlier capture limitations remain disclosed. No duplicate full suite was run solely for publication.

## Access, integrity and boundaries

[Publication manifest](PUBLICATION-SHA256SUMS.json), [bounded exact-byte mirrors](MIRRORS.json), [data-only verifier](verify_publication.py), [verifier output](PUBLICATION-VERIFICATION.txt). Text-only tools can concatenate/decode the listed base64 parts to reconstruct the exact SQLite, JPEG and large text/export bytes without ZIPs or Mac access. Readable row exports supplement raw bytes. All nine original walkthrough artifacts remain unchanged. No credentials, signing keys or signed read tokens are included in this supplement. Earlier token-redaction limitations remain with the previous evidence.

These are implementation-operated browser captures and data-only publication checks, not an independent live browser witness, complete network trace, signature authentication, live delivery-fault exercise or clinical validation. Full-set in-memory recovery remains deferred. Existing actor/source identities are assertions.

PR #23 remains draft/open/unmerged at application head **17e2064c3f1a1761876e9a42c5c7a131646d465c**. Separate review tags expose the correction and evidence; its application branch is not updated. The live local workspace at 5191 still serves the captured fa8ce7d build; it was not replaced or reloaded during this correction/publication. Accepted read-only Docker evidence remains separate and unchanged.

**Production connected execution stays disabled. No merge, deployment, external demo hosting, gate activation or clinical-readiness approval.**
