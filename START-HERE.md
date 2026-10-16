# ClinRx Director — echo production wording correction

Two-file synthetic-demo presentation correction, submitted through PR #23 without a ZIP or Mac access. Production connected execution stays disabled. No merge, deployment or gate activation.

## Exact identities

Source: [79536d42701e5153acdd94bf04844c353c25190b](https://github.com/shafin-lab/clinrx-ai/tree/79536d42701e5153acdd94bf04844c353c25190b)

Tree: `ad4d5f9c5e1b29a867f24081e1c896753e2c3a04`

Parent: `131f3413a664b05ad898518f3ce998715d08b53d` (accepted ABG/echo overview and closed bottom-scrolling gap).

[Exact two-file diff](https://github.com/shafin-lab/clinrx-ai/compare/131f3413a664b05ad898518f3ce998715d08b53d...79536d42701e5153acdd94bf04844c353c25190b), [complete patch](source.patch), [source identity and validation metadata](source-identity.json), [raw commit](source-commit.txt), [committed source copies](source/frontend). Separate review tags leave PR #23's draft/open application head unchanged at `17e2064c3f1a1761876e9a42c5c7a131646d465c`.

## Correction

Echo cells now label the unchanged raw field as “Recorded production tag”. Qualitative echo findings additionally use the inspector's existing clarification: “Qualitative echo findings are source-report assertions, not directly measured diagnoses. The recorded production tag is preserved as supplied.” Numeric estimates retain their production tag without the qualitative-only text. Source fields, report caveats, raw values/units, source-time placement, uncertainty/status, grouping, clicks and execution behavior are not changed.

The only changed files are overviewEvidenceContext.ts and its existing flowsheetOverview.test.tsx regression assertions. Backend, fixture data, schemas, policies, dependencies, migrations, transport, CSS, execution configuration and screenshot tooling in the application are unchanged.

## Relevant checks

- [Focused overview log](original/focused.log): all 9 tests passed, 5.47 seconds; exact command in metadata. Existing ABG/echo regression now asserts the qualitative clarification, preserved PH report limitations and absence of qualitative-only text on numeric RVSP. Existing immutable-source comparison remains.
- [Typecheck/default build](original/build.log): TypeScript and Vite passed; existing bundle-size warning persists. Whitespace check passed.
- [Tested-file hashes](original/tested-source.sha256) match both committed source files. Tests ran before committing these same bytes. No duplicate full-suite, backend, hosted CI, hosted-mode or container run was needed or performed. Previous 526-test acceptance is not relabeled as a new run of this correction.

## Browser and screenshot extension

[Corrected qualitative echo screenshot](original/qualitative-echo.jpg) and [complete captured DOM](original/current-dom.txt) show m7-PH/1 at its original 08:00 column, unchanged source wording/limitations, the corrected label and source-report clarification. These were captured on the final tested working tree before commit against the existing real local API; not a Director live session or complete network trace. No new API/database export is claimed.

The new screenshot has JPEG magic bytes and a matching .jpg filename, saved without conversion. For future evidence captures, inspect actual image bytes before choosing .jpg/.png; reject unknown formats instead of guessing. No retrospective conversion, rename or replacement of accepted screenshots occurred. The application's transport/data and screenshot capture behavior were not modified.

## Preserve prior evidence

The original [accepted ABG/echo evidence](https://github.com/shafin-lab/clinrx-ai/tree/727e049ed099b5bf2a9911d12439940d880b2f09) and [accepted scrolling supplement](https://github.com/shafin-lab/clinrx-ai/tree/f2ff86b04d22411b3bd4d23e799f0f7fdb6c3ec4) remain untouched, including their historical JPEG bytes under .png names. Their existing manifests were rechecked locally and passed; this is implementer revalidation, not fresh Director review. [Raw revalidation output](prior-evidence-verification.txt).

Original local capture notes and checksums are preserved under original/; their “uncommitted” wording describes that earlier capture, not this published source.

## Independent review requested

Recompute [manifest](SHA256SUMS.json), raw commit identity, both source/tested-file hashes and screenshot file signature. Inspect the narrow wording diff and source/qualitative regression assertions. Confirm raw production fields/report caveats are preserved and no new diagnosis or execution behavior is introduced.

[Portable verifier](verify_evidence.py), [implementation verification result](verification-output.txt). Distinguish independently recomputed evidence from inspected implementation-produced execution logs.

Return a bounded verdict on the correction and extension-handling practice. Preserve all previous acceptance; no fresh full-suite rerun is requested solely for wording. Keep production connected execution disabled. Do not modify the repository, merge, deploy, host or activate gates; no clinical validation is inferred.
