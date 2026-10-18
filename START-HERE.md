# PR #23 — local synthetic evidence entry review

Application source: **5e204af79c370bf61e8676b2c6191e5d08cd7d9b**  
Git tree: **8294161c6f90f6961c5b651306f497c4dc68d16c**  
Base: **d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982**

[Exact source](https://github.com/shafin-lab/clinrx-ai/tree/5e204af79c370bf61e8676b2c6191e5d08cd7d9b) · [Ten-file increment](https://github.com/shafin-lab/clinrx-ai/compare/d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982...5e204af79c370bf61e8676b2c6191e5d08cd7d9b) · [Workflow and isolation](https://github.com/shafin-lab/clinrx-ai/blob/5e204af79c370bf61e8676b2c6191e5d08cd7d9b/docs/SYNTHETIC-EVIDENCE-ENTRY.md)

## Start with these artifacts

- [Original local report](original/README.md). Its “nothing pushed / not yet linked to PR” statements describe capture-time status; this new publication supersedes only that publication status. All other limitations remain.
- [203 targeted backend tests](original/backend-targeted-final.log), [561 frontend tests](original/frontend-final.log), [normal build/typecheck](original/default-build.log), [authoring build/typecheck](original/authoring-build.log), [exact tested/committed source hashes](original/source-hashes.json).
- [Final-build CO review screenshot](original/final-co-review.jpg), [saved correction screenshot](original/final-co-complete.jpg), [complete review DOM](original/final-co-review.dom.txt), [saved/history DOM](original/final-co-saved.dom.txt).
- [Database checks and exact original/successor payloads](original/database-checks.json), [SQLite bytes](original/database.sqlite3), [all table exports](original/tables.json), [readable per-row table index](readable/tables-index.json).
- [Fresh authoring snapshot, signed token redacted](redacted/state.json), [157 item index](readable/state-index.json), [unchanged accepted Docker snapshot, token redacted](redacted/accepted-docker-state.json), [156 item index](readable/accepted-docker-state-index.json).

## Byte access and credentials

[Original manifest](original/SHA256SUMS.json) records all 27 local capture artifacts. **25 are published byte-for-byte; two raw state-response files are intentionally withheld because they include temporary signed state contexts.** [REDACTIONS.json](REDACTIONS.json) identifies those original hashes and the redacted copies. Only the top-level token value changes semantically; source data, scope, cutoffs, ingestion, assembly digests and disabled-gate fields remain. The original local files and manifest were not edited. Do not claim raw token bytes are publicly recomputable or authenticated.

[Publication checksums](PUBLICATION-SHA256SUMS.json) cover every published artifact. [MIRRORS.json](MIRRORS.json) gives bounded base64 part paths, byte lengths, SHA-256 and Git blob IDs for each binary, NUL-containing or >40 KB file. Concatenating and decoding the listed parts reproduces the exact published bytes, without ZIPs or Mac access. Screenshots remain JPEGs with `.jpg` names. Readable row/item exports supplement rather than replace raw files. [verify_publication.py](verify_publication.py) performs data-only checks; running the application or clinical code is unnecessary for artifact integrity review. Its output is in `PUBLICATION-VERIFICATION.txt`.

## Review the new increment only

Source imports across the existing 15 M7 contracts; selection and raw-value correction; withdrawal; actor/reason preview; immutable append; exact predecessor/repository checks; canonical idempotence; stale conflicts; bounded history; uncertain completion and explicit same-revision recovery/retry. Inspect the separate local gateway boundary and verify normal/read-only entry points never install authoring routes. This is an initial structured-record import tool, not completed clinician charting forms or authenticated clinician identity.

The new database was seeded with 156 items / 162 revisions / two retained synthetic receipts. Four browser appends leave 157 items / 166 revisions / two retained receipts: pH correction, fictional import, withdrawal, final-build CO correction. Original pH 7.35 and CO 4.60 remain; successors are 7.36 and 4.61. CO source time, suspect quality and acquisition context remain. Earlier pH/import/withdrawal captures preceded the final UI refinements; only `final-co-*` represents the final build. The seed's HPI absence is optionality, not a missing mandatory measurement.

Before/after immutability and receipt preservation are tested separately. The exported database is an after-exercise checkpoint, not a historical before-image. Browser evidence is implementation-captured, not an independently witnessed live exercise or complete network trace. Lost-response paths are tested, not newly live-injected here. Reload/closure can lose pending in-memory commands. No new patient interpretation or clinical validation is established.

The early explicit-retry timeout cause remains unresolved. The mixed overlapping-run log is inconclusive and is preserved as such; use the separate clean final log. The final retry test uses the actual visible source filter; no timeout threshold or assertion was relaxed. No duplicate full suite is requested solely for this publication. No full-backend, new hosted CI or container validation is claimed.

PR #23 remains draft/open/unmerged at application head **17e2064c3f1a1761876e9a42c5c7a131646d465c**. Source and evidence are separate immutable review tags, not an update of its application branch. Earlier bounded Docker acceptance at d0f94dc is preserved, not extended to this authoring increment. Production connected execution stays disabled. No merge, deployment, external hosting or gate activation.
