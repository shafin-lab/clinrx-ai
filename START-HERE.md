# RF2 usability: one combined Director review

Application **195f4521002253d738685bf644564d51eb1acf4e**; tree **564789187c83b4250fa1fa502204b23d091375f4**.
Includes usability commit8186bb72b6748372e229b8fe40548af14c90f238 on accepted F2 baseline6972799580d73478adce1068c30e3b14348ccc4e.

1. Read [usability report](original/usability-8186bb7/REPORT.md) and [final feedback-placement report](original/feedback-195f452/REPORT.md).
2. Review [final six-file manifest](candidate-source/FILES.json), [combined diff](candidate-source/changes.diff) and both raw commits. Production changes are three frontend source files; three test files accompany them. Backend, backend tests, configuration, CI, schemas, policies, storage and gates are unchanged from6972799.
3. Inspect original logs: **79 focused /754 full frontend tests** belong to8186bb7. Final195f452 has **41 focused tests across3 files**, typecheck/default and explicitly RF2-enabled builds. No final-head full-suite, hosted CI or container result is claimed. The initial78-pass/one fixture failure remains disclosed. Initial authoring build without HOSTED was not the installed RF2 build; final mode flags are explicit. Existing bundle warning remains.
4. Compare each installation's before/after twelve-table exports and UPDATE.json. Both preserve186 fact revisions and2 receipts. Served HTML/JS/CSS match tested builds by direct HTTP; this is not a browser resource trace. Backend process was retained, its source tree equals the final candidate, preserving signing context. Browser storage was untouched/not inspected. No automated browser reload occurred.
5. [MIRRORS.json](MIRRORS.json) supplies exact lossless text/base64 parts for large originals; no ZIP or Mac access required. Original manifests are preserved. PUBLICATION-SHA256SUMS.json covers the complete published package except itself. Run verify_evidence.py for data-only integrity verification; it does not run the application/tests/browser.

## Requested checks

- Legacy event recorded_amount uses the original-owner editor's single authoritative draft. Simple numeric field and advanced JSON stay in sync; raw unit, interval, availability, other fields and original revision remain unchanged. No quantity is invented for absent/qualitative evidence. Proposed amount/raw unit are visible before append. No dose/rate calculation is added. Four-place input text is tested in the draft; no new server-side formatting guarantee is claimed.
- Disabled event-correction controls explain draft/review/busy/unconfirmed-gate/pending-command blockers. Explicit discard remains required; no automatic reset/remount/retry.
- Required Actor and note fields are named before transport. Draft values/exact selections survive. Final validation/review/save/recovery alerts appear once next to draft controls; source-history errors remain near sources. No automatic focus jump or validation/transport bypass.
- Preserve source-review consent, repository isolation, exact recovery, explicit retry and handover behavior.

## Assisted observation boundary

User screenshots in this conversation showed the named missing-field alert and unsaved-draft explanation at8186bb7, then an Actor-required alert directly below Validate/Discard at195f452. That last capture was a new source-record form, not the six-field note form. User reported discarding the test draft. No new saved record was requested. No screenshot demonstrates the new amount field. These observations are assisted/user-supplied, not independently operated browser testing.

Screenshots include unrelated chat/sidebar content; none are published here. Therefore this package requests source/test/data acceptance, NOT independent screenshot/reload acceptance or closure of broader RF2-12. Prior screenshot evidence gap remains. No repeated successful journey is supplied or required for these narrow changes.

This publication uses separate source/evidence tags; PR23 application head remains unchanged. Accepted F1/F2/F3 and prior RF1/hemodynamics scopes remain preserved. RF2-F4 and general durable draft/command recovery remain open. Execution stays disabled; no merge, deployment, external hosting or activation. No clinical-readiness claim.
