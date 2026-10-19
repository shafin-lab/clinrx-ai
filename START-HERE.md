# RF1 — one combined implementation review

Application: `c2d58e4c8d52d2ceeddd57881365cc5f76cdf74f`  
Tree: `960105b34b302648190fa40630725573e893edce`  
Baseline: `b4194447829f060387b816437694af9f6c0cb60e`  
Approved specification: `7fa529dd276ceb140700760a358cf3493b44e85b`.

This is a NEW implementation review. Specification approval is not code acceptance. Read [the original combined report](original/README.md), [final results](original/validation/final-results.json), [exact source diff](original/validation/source.diff) and [tested files](original/validation/tested-files.json). The application source is separately available at its exact GitHub review tag. This evidence tree does not update PR #23's application branch.

## Scope and six conditions

Local, opt-in, read-only renal/fluid review in the shared synthetic patient workspace. Review raw original creatinine observations (including missing/unplaced); one repository/patient/encounter/window/cutoff; shared aggregate accounting and combined size limits; fail-closed scope/context/digest/reference checks; terminal/history semantics without substitution or resurrection; no fact/receipt writes during the journey; renal authoring, mixed-kind notes/handover and calculations deferred. Generic observations retain their legacy contract; withdrawal/suspect-quality examples use circulatory records.

## Final local validation

4,318 backend tests passed (one existing warning; 1,058.32s), including 16 new RF1 API/storage checks. Final full frontend: 696 passed / 22 files, 53.79s, maxWorkers=2. Typecheck, default build and RF1 authoring build passed; dependency pins consistent; migration m7_0008. All 20 changed file bytes match the local commit. Tests/builds preceded commit against matching bytes; no clean-archive rerun or hosted CI is claimed. Local Node 24.12.0 / npm 11.6.2 / Python 3.11.6. Existing bundle-size warning remains.

The first fixture attempt duplicated two already existing sample identities; final fixture setup reuses the originals. Quantity rendering and test import/type errors were corrected. Later pre-final frontend runs had 695 passes/one navigation timeout and 20 passes/one panel timeout. Final navigation testing isolates the unchanged heavyweight screens, retaining the real renal panel/shared hook/client and all assertions. Final full suite passes without timeout/threshold relaxation. Timing contributors are not all established. Preserve the raw earlier logs; do not relabel them as final success.

## Inspect evidence without Mac access or a ZIP

- [All original artifact hashes](original/SHA256SUMS.json); [publication hashes](PUBLICATION-SHA256SUMS.json); [lossless mirrors](MIRRORS.json); [file index](INDEX.md).
- [Final API context](readable/final-context.json), [168 exact source-item index](readable/api-index.json), [all table-row index](readable/tables-index.json).
- Three actual SQLite checkpoints: original/evidence/before.sqlite3, after.sqlite3 and final.sqlite3, with all-table row exports. All 12 tables, 175 fact revisions and both retained receipts remain unchanged. The final snapshot extends through the closed-gate rejection probes. Signed read contexts are redacted from response/request exports; formatting changes for readability, so raw-byte HTTP equality and signature authentication are not claimed.
- The original data-only verifier refers to a Mac-local baseline. `verify_publication.py` is the portable equivalent, using baseline-rows-publication-copy.json, a publication-time read-only row copy of the existing 167-fact workspace. That is not a new contemporaneous before-journey checkpoint. It verifies prior-fact and receipt correspondence separately from the RF1 three-snapshot no-write interval.
- Final runtime is the isolated workspace on 5197; the original 5195 workspace was not replaced. Fixture appends precede the journey and are disclosed separately from read-only operations. No startup seeding/reset occurs.
- Final build bytes are included in final-build/, with their original build hashes. Events 1–6 and earlier captures belong to a pre-focus-polish iteration; final asset loading begins at event 7, with final composite/history/interval responses 10/11/12. Final-build fact correspondences: 171; aggregate across both iterations: 341. Only final-prefixed captures support final UI claims.
- Browser screenshots are actual JPEGs with .jpg extensions. Complete DOM/AX captures supply off-viewport fields; screenshots do not show all records simultaneously. A 575×823 layout records document width 575 and contained table overflow. This is an implementation-operated captured journey, not independent uncoached usability, all-device/accessibility certification or a complete authenticated network trace.

## Publication boundary

Original 90 artifacts/checksums are preserved. The original report and final-results.json say source publication/CI were outstanding: that is their earlier validation-time status. This later evidence publication makes source/artifacts accessible; it does not create hosted CI or approval. Mutable runtime databases, private helper read tokens, signing keys, credentials and unrelated local files are excluded. Lossless base64 parts allow inspection/reconstruction of large/binary originals; no ZIP is needed.

Return one combined verdict on implementation, regressions, actual source/data correspondence, six conditions and remaining gaps. Preserve prior hemodynamics/M1/C1/R1/F1/F2 acceptances in their original scopes. No duplicate application suite is requested solely for publication. Independent code acceptance and exact-candidate hosted CI remain outstanding.

Execution stays disabled. No merge, deployment, external hosting, clinical validation, new container acceptance or gate activation is authorized or claimed.
