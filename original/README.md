# C1 — duplicate decoded members in retained reassessment references

Corrected local source: db56f7e8164a7a3c46c6c8e17a56c0d9088c2de5
Tree: a60dedfbb8e4f7ecfb82ad8467e3895cde36372b
Parent: ebbab2955109884169ae7ceef4a87d0f12af4ebf

Three-file narrow correction: retainedReassessmentReference.ts parses a flat object with exactly one decoded kind, id and version, all nonempty strings. It parses individual JSON string tokens, never an object that could already have lost duplicate keys. Decoded names are checked for duplicates before constructing a reference. Existing exact-association/encounter validation remains in place. No stored note, historical contract, source fixture, backend, execution configuration, dependency or CSS change.

Old-code negative control reproduced six conflicting duplicate kind/id/version cases including escaped equivalent names. Raw log reports six expected failures, 26 skipped; each test establishes native JSON.parse resolves to the exact supported last-member reference before asserting withholding. Corrected tests also check the rendered warning, unchanged input, identical duplicate members, valid whitespace/order/escapes/escaped punctuation, and invalid grammar. Existing ambiguity, missing/foreign/mismatched associations, tuple collision, selection preservation, entry/correction/recovery checks remain covered.

Final narrow suite: 49 passed across two files in 8.64 seconds. Final typecheck/default build and authoring build passed, with existing bundle-size warning. Exact commands/exit codes/versions/source hashes in validation.json. No duplicate full-suite/backend/hosted-CI/container run. Node 24.12.0/npm11.6.2 were used for this correction; do not attribute earlier Node22 validation to it.

An initial typecheck failed because the integration's ExactRef type import was removed while its return annotation remained; the import was restored before final tests/builds. Both initial failure logs and the preceding 49-test run are preserved separately. The final source and tests were validated before the local commit; hashes match the committed bytes. No clean-archive rerun is claimed.

This package is local only. The running 5191 workspace remains on the earlier ebbab29 build; the corrected authoring build is prepared separately here. No fresh browser or API/database exercise, source/authentication trace or new persisted state follows from these tests. Prior source, validation and walkthrough artifacts are unchanged. Director's bounded walkthrough acceptance remains separate from C1 code re-review. As Director clarified, the earlier expanded-notes.txt had only A provenance content displayed; final.txt established both. No earlier original is rewritten.

Production execution remains disabled. No push, merge, deployment, external hosting or gate activation. Durable browser-session recovery remains deferred. Independent C1 closure is still pending Director re-review.
