# M1 — repository identity continuation correction

Source: `b4194447829f060387b816437694af9f6c0cb60e`  
Tree: `eb6ed9d3f53727ccf186c1cb3ee5b5ba9f2677df`  
Parent: `ee81661d7ae70d6ab5491a2da8634f675381d00a`

## Correction

Only the internal comparison component is keyed by the JSON tuple of repository,
patient and encounter. All comparison choices are cleared synchronously at that
boundary, so a reused note identity cannot become an implicit new selection.
Same-scope snapshot refresh/reordering keeps the existing choices. The outer
patient workspace, evidence editor, retained confirmation and pending command
are not remounted.

Saved-result callbacks carry the confirmed response's repository ID alongside its
exact reference/digest. The workspace checks it against the active repository
before attempting source lookup or handover addition. The editor also disables
those two actions with an explicit explanation on a repository mismatch, retaining
the original saved confirmation. A new blank entry/reassessment remains an explicit
separate action; it does not reuse the saved record.

Seven additional regressions cover repository/patient/encounter comparison resets,
same-repository selection retention, integrated explicit reselection/handover,
identical reference/digest in a replacement repository, and uncertain pending draft
preservation through a repository refresh with exact lookup of the original request.

## Validation

- Old-code negative control: 5 failures / 1 passing same-repository control, 57 skipped.
  These are test reproductions, not live adversarial browser probes. The separate
  pending-draft regression was added afterward.
- Final focused tests: **119 passed across 6 files**, 16.10s Vitest duration.
- Final full frontend: **675 passed across 21 files**, 43.46s Vitest duration.
- Typecheck, default build, authoring build and whitespace check: **passed**.
- Authoring build explicitly sets `VITE_SYNTHETIC_AUTHORING=true`; `run-check.py`
  records that environment behavior. Commands, exit codes and wrapper elapsed times
  are in the individual JSON files. Node/npm versions are in environment.json.
- Existing bundle-size warning remains. No timeout or assertion threshold changed.
- Tested-file hashes match the locally committed bytes; working tree is clean.

The first corrected focused run reported 80 passing / 1 failed (three files): one
new handover assertion supplied a string instead of the structured description
field expected by the renderer. The test fixture was corrected to raw_display,
then the final focused and full checks passed. The initial log is retained as
focused.log; it is not relabelled as final success. An initially mistyped guided
test filename did not match that file in the initial run; focused-final includes
the actual guidedEvidence.test.ts and entry-client/local-handover tests.

## Evidence preservation and attribution

`EVIDENCE-ERRATUM.md` corrects START-HERE step 6 from evidence commit
`3c823a0182c4a7f69cf235fe020e435b712e6a5b`. Captures 12/13 show expanded
narratives, while inner uncertainty/provenance disclosures remain collapsed.
No new capture is substituted and the old report is not rewritten.

The original publication's data-only verifier was rerun read-only: all 834
publication hashes, 84 original hashes and 21 mirrors/719 parts still pass.
See original-evidence-preservation.json. Its API/database/runtime results remain
attributed to ee81661; rerunning its verifier is not a new browser or database
exercise on this correction.

This is six changed files: three frontend components, two regression files and a
separate documentation erratum. No backend/schema/policy/fixture/dependency,
migration or production execution configuration changed. No backend suite rerun,
new hosted CI, live browser exercise, container validation or runtime update is
claimed. The already-running local page was not replaced in this task.

No publication, push, PR change, merge, deployment or external hosting occurred.
Production execution remains disabled. M1 acceptance requires Director's re-review;
prior C1/R1/F1/F2 closure and bounded acceptances remain separately attributed.
