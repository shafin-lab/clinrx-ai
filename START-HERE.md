# RF2 implementation — single combined Director review

Application: **44294015e5439f581c8107bb7a0f72a77f328406**; tree **eb1d921cba282bc8cce208f1282c0cd9e0a969e4**.
Approved specification: a4547e215a8c4c20bd04e807d0287c5e1d575c39. Baseline: 5cb73212ae6104b02bad361886cd9507795d88bf.

1. Read [combined report](original/MILESTONE-REPORT.md), [RF2-01–RF2-12 matrix](original/ACCEPTANCE-MATRIX.md) and [exact-candidate CI](original/CI-RESULTS.md).
2. Inspect [ownership/carrier mapping](original/source/files/docs/rf2/OWNERSHIP-AND-CARRIERS.md), [source identity](original/source/IDENTITY.json), [22-file source manifest](original/source/FILES.json) and [full diff](original/source/change.diff).
3. Inspect timestamped HTTP events, exact request bytes, redacted response bodies and SQLite checkpoints in original/api-journey/. Final runtime admission/owner/recovery evidence is separate under original/ownership-revalidation/; original/final-revalidation/ is the preceding narrow supplement. All original bytes/checksums are preserved, excluding mutable runtime files.
4. For large text or binary files, [MIRRORS.json](MIRRORS.json) lists lossless parts, lengths, hashes and Git blobs. UTF-8 parts concatenate directly; base64 parts concatenate then decode. No ZIP or Mac access is required. Original database row exports provide readable inspection alongside the exact SQLite bytes.
5. Run [data-only verifier](original/verify_evidence.py) from original/ if execution is available. [Recorded result](original/DATA-VERIFICATION.json) is implementation evidence, not a substitute for independent recomputation. PUBLICATION-SHA256SUMS.json covers all published files except itself. Existing original manifests remain unchanged.

**Attribution:** positive HTTP/API journey used 11ddd8a, not the final candidate. Final source guards were separately checked at 4429401 with unchanged twelve-table data and matching served build bytes. Exact-candidate hosted CI passed **4338 backend / 739 frontend**, typecheck, default and explicit RF2-enabled builds. Four supplemental handover component cases are outside frozen source and not added to 739. Earlier failures/cancelled runs retain original attribution.

**Remaining gap:** browser access was denied by tool security policy. No alternate surface was used. RF2-12's live desktop/narrow viewport, keyboard/focus/scrolling, accessibility and uncoached usability are NOT established. Saved-handover storage/reload is component evidence, not a captured live-browser exercise. General durable draft/command recovery remains deferred. Do not infer complete milestone/clinical acceptance from CI.

Only synthetic evidence is published; the repository is currently public. No signing keys, credentials or mutable runtime files are included. A successful-response discard after the actual API return and pre-dispatch absence are the exercised fault models, not socket loss or rollback proof.

Please issue one combined verdict, distinguishing accepted source/API/component scopes from RF2-12 gaps and any required corrections. Preserve RF1-F1 and hemodynamics acceptances. RF2 is a bounded M8/M9 contribution, not completion of those modules. Keep execution disabled; no merge, deployment, external hosting or gate activation.
