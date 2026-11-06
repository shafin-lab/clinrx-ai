# M11 bounded integration and usability handoff

5 November 2026. Base: merged M11 `ba1fc2f`. The bounded functional checkpoint is `7a86faf`. The user has authorized GitHub integration after independent verification; M12 is not started and mobile remains deferred. The existing previews and patient data must remain unchanged throughout publication.

## Resulting behavior

The patient workspace retrieves shared RF2 evidence once and then antimicrobial evidence at exactly the same repository, watermark, capture timestamp and review window. Each microbial item must have the expected canonical fact digest and a positive safe ingestion sequence within that cutoff. The legacy combined endpoint remains available.

The 2 MiB response limit remains unchanged. Accounting uses compact UTF-8 JSON as sent and still rejects oversized responses without truncation. A previously decoded catalog is reused without decoding or mutating it a second time.

GI Overview presents the latest exact-time finding for each exact category/title, with earlier observations expandable. Tied, unknown and bounded observation times remain visible. Missing critical-flag status is summarized per displayed report set, with the exact report, component and result attributable in its disclosure. Repeated mapped tests receive component identifiers in the table. Actual critical, interference and conflict qualifications remain beside affected results. Original source detail and correction/withdrawal history remain inspectable.

## Verification

The maintained local suites passed: **1,805 frontend tests**, with three existing skips; **4,559 backend tests** across four disjoint partitions covering the full collected suite; TypeScript checking; default and configured production builds; and whitespace checks. Existing large-chunk and Starlette test-client deprecation warnings remain. Final publication additionally requires green GitHub CI on the exact PR head and equality of the merged and tested source trees.

A fresh independent review of `ba1fc2f..96e0369` found two Important issues and no Critical or Minor findings. Canonical microbial source integrity/ingestion bounds and repeated laboratory component attribution were corrected at `7a86faf`, with failing regressions observed before correction. The focused correction suite passed all 20 tests; the full maintained suites above passed afterward. No post-fix independent re-review is claimed.

A larger isolated fictional patient copy was used to verify populated M6–M11 integration: one original PT/INR report across M10, M11 and Patient overview; earlier and corrected liver results; latest/earlier feeding observations; procedure and withdrawn-report history; the existing populated ABG/support progression; and blood-product fluid accounting without duplicate counting. No original patient store was used for verification writes.

Native two-tab checks verified pending ownership after a successful source commit whose confirmation was deliberately lost. Reload and exact lookup recovered one committed source without a second append; the competing editor could not overwrite it. A native Web Lock held the first review save while a competing review was blocked. On release, exactly one review saved and survived reload. The final normal verification preview serves frozen source without the test wrapper or controls.

Preservation checks confirmed unchanged hashes and integrity for the eight pre-existing protected databases and all 607 files across three earlier served builds. The new verification copy/build are also protected during GitHub integration. No preview restart/deployment, patient migration/write or browser-review mutation is part of publication.

## Coordination and publication boundary

ClinRx main work received the verification handoff but did not undertake the requested checkpoint review. The user subsequently authorized proceeding with independent verification instead. Do not claim joint verification. The integrating owner is responsible for source-only publication, fresh GitHub CI, a merge pinned to the reviewed head, and final preservation checks.

Local copied databases, source-evidence captures, browser storage, private keys, runtime files, dependency directories and built assets are excluded from publication. Only the reviewed source, tests and sanitized project documentation are included. The original local evidence and rollback assets remain preserved.

## Remaining attention before further expansion

- Existing laboratory Latest/Earlier specimen headings still need a separate correction for tied, unknown or sub-millisecond sample times. Exact source times remain available.
- Individual evidence reads remain bounded at 2 MiB. Bounded pagination is future work before larger admissions exceed a single slice.
- Dimensionless INR units are rendered as `1` in M10/M11 result tables, while overview omits them; this remains a small readability follow-up.
- Reviews remain browser-local synthetic records, not an authenticated shared clinical audit store. Clinical execution and advanced GI treatment inference remain disabled.
- Mobile verification and M12 remain deferred. A GitHub merge does not deploy or replace an existing preview.
