# M1 repository-identity correction — focused re-review

Application: `b4194447829f060387b816437694af9f6c0cb60e`  
Tree: `eb6ed9d3f53727ccf186c1cb3ee5b5ba9f2677df`  
Parent / reviewed milestone: `ee81661d7ae70d6ab5491a2da8634f675381d00a`

Start with [the original correction report](original/README.md), [the exact six-file diff](original/correction.diff), [source identities](SOURCE.json) and [the separate wording erratum](original/EVIDENCE-ERRATUM.md). Source mirrors are in source/.

Review whether M1 is closed: repository/patient/encounter changes must reset only comparison choices, require explicit reselection and prevent implicit rebinding of a reused note tuple. Saved-result callbacks must retain the confirmed repository and withhold continuation against a different repository even when reference/digest match. Preserve same-repository choices, mounted editor, uncertain pending request and exact lookup/retry guarantees.

## Validation and provenance

- Seven added regressions. Old-source negative control: five failures, one passing same-repository control; pending-draft regression added afterward.
- Final focused: **119 passed / six files**. Final full frontend: **675 passed / 21 files**. Typecheck, standard/authoring builds and whitespace passed.
- Original raw logs, exact commands/exit codes, environment, tested-source hashes and initial failed run are retained in original/. Initial corrected focused failure was a new test fixture with the wrong narrative shape; it was corrected and final focused/full checks passed. No timeout/assertion relaxation.
- All six tested-file hashes match committed bytes. Tests/builds preceded the commit, not a clean-archive rerun. Existing bundle-size warning remains.
- Original milestone package at `3c823a0182c4a7f69cf235fe020e435b712e6a5b` remains unchanged. The read-only preservation check verifies all 834 publication hashes, 84 originals and 21 mirrors/719 parts. This is not a new API/database/browser exercise on b419444.
- Erratum: captures 12/13 show expanded narratives; inner uncertainty/provenance disclosures remain collapsed. No original capture/report/manifest is rewritten or substituted.

This package publishes the existing validation artifacts without rerunning tests solely for publication. The original report's “no publication/push/PR change” statement describes its creation-time status; this wrapper records the later authorized publication. The source/evidence are published through separate immutable review tags; PR #23's application branch remains unchanged.

## Access and limits

No ZIP or Mac access is needed. Original files are present as bytes; large files also have lossless bounded base64 text parts indexed by MIRRORS.json. `python3 verify_publication.py` performs only data/hash/Git-identity checks, never app/tests/server execution. Recompute independently if preferred. ORIGINAL manifest remains original/SHA256SUMS; root SHA256SUMS covers this publication. These are publication-time commitments, not capture-time attestations.

No new hosted CI, backend run, browser exercise, runtime update, container validation or clinical-readiness acceptance is claimed. ee81661 CI and browser/database evidence keep their original attribution. The running local page has not been replaced by this correction. Prior C1/R1/F1/F2 and bounded acceptances remain separately preserved.

Production execution remains disabled. No merge, deployment, external hosting or gate activation. Return one focused M1/code/evidence re-review; no duplicate ABG walkthrough or suite is requested solely for publication.
