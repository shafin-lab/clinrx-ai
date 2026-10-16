# Local echo wording correction

Uncommitted two-file increment over accepted 131f3413a664b05ad898518f3ce998715d08b53d.

Echo metadata now says “Recorded production tag”. Qualitative echo cells use the existing inspector clarification: “Qualitative echo findings are source-report assertions, not directly measured diagnoses. The recorded production tag is preserved as supplied.” Raw source fields, original findings, PH caveats and sample/time behavior are unchanged. Numeric estimates do not receive the qualitative-only clarification.

Checks, 17 October 2026 (Asia/Kolkata):
- Focused overview suite: 9 passed; 5.47 seconds.
- Typecheck/default build: passed; existing bundle-size warning remains.
- git diff --check: passed.
- Browser: qualitative PH source wording and complete clarification observed at original 08:00 column.
- Reviewed ABG/echo evidence: original 34-entry and nested original manifests still pass.
- Reviewed bottom-scroll evidence: all 8 manifest entries still pass.

Original reviewed evidence remains untouched, including mislabeled historical screenshots. Future captures must inspect image magic bytes before selecting the filename extension: JPEG → .jpg, PNG → .png; unknown formats should not be given a guessed extension. New qualitative-echo.jpg was detected as JPEG and stored without conversion.

No full-suite rerun, backend test, publication, hosted CI, container validation, merge or deployment. Production gate configuration and backend are unchanged; captured DOM retains the execution-disabled banner.
