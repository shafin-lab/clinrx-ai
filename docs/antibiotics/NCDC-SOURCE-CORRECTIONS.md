# Targeted NCDC source-to-screen corrections

Historical checkpoint: this targeted renderer is retained as existing work. The active library now uses the complete NCDC projection described in NCDC-COMPLETE-COVERAGE.md and NCDC-COMPLETE-HANDOFF.md. In particular, its former treatment-option/source-branch UI is superseded by complete first-line and alternative source columns; the verification below applies to the earlier checkpoint only.

Scope: the user’s examples in endocarditis (section1.1), acute/chronic osteomyelitis (10.1/10.2), plus PDF column wrapping. This continues the NCDC-only library; no supplemental source, renal adjustment, prescription path or patient-data change is introduced.

## Source and representation

The retained NCDC Version2 November2025 PDF is authoritative. PDF21–22 supplies endocarditis treatment, comments and empirical-treatment context. PDF67 supplies acute osteomyelitis contexts and the shared 4–6-week duration. PDF68 expressly refers acute-on-chronic disease accompanied by fever to the acute guidance.

- Endocarditis primary/alternative source options are shown one at a time. Individual agents retain their own durations, route choices and maximum doses. The prosthetic daptomycin row does not inherit a route/duration from another row.
- The native-valve penicillin G/gentamicin scope and the alternative-cell connector remain source ambiguities. They are readable source branches with explicit warnings, not silently assembled combinations or complete monotherapy regimens. The contiguous ampicillin + gentamicin combination is represented separately.
- The teicoplanin branch retains its three-dose loading stage and literal source maintenance wording. The missing maintenance /kg basis is flagged, never supplied by inference. Its total teicoplanin duration is not borrowed from another branch.
- Chronic guidance points by identifier to the existing acute infection. The clinician selects the applicable acute pattern in the same panel; the treatment and its PDF67 provenance then appear automatically. No new clinical observations or duplicated dose records are created. Self, missing, empty-target, cyclic and mixed direct/reference data are rejected.
- Management comments are visible beside the relevant guidance. Soft PDF line wrapping is reflowed into paragraphs; deliberate blank-line separation between drug components remains.
- The complicated acute osteomyelitis primary text remains visibly marked as a source branch requiring clarification, including its vancomycin dose-basis anomaly. Its source alternative remains separately selectable without an inferred route.

Data comparison shows changes only in sections1.1,10.1,10.2; all source identities, group identities and other infection objects are preserved. The generic referral matcher now recognizes phrases split across PDF lines. No fuzzy or cross-source referral resolution is performed.

## Verification

Focused frontend regressions:57passed. New reported-behavior tests failed before implementation. The parser regression fails with the previous matcher and passes with the corrected matcher. Typecheck passed. Final full frontend suite: 1,540 passed, three skipped; parser regression: one passed. Typecheck, production build and whitespace checks pass. Independent review approved the bounded corrections with no Critical/Important findings; its minor stale-note finding was removed. Browser verification covered native/prosthetic/severe-sepsis options, explicit teicoplanin warning, chronic reference selection and source provenance, and readable prose. Original preview assets and both patient database hashes remain unchanged and pass integrity checks. Existing large-chunk warning remains; backend unchanged and its full suite not rerun. These results do not validate all remaining catalogue holds.

The prior NCDC-only build is preserved in ignored `review-evidence/infection-library/source-corrections/previous-build/`; the original preview at5246 remains untouched. Candidate update stays on5247 with the same database and browser origin. Mobile checks remain deferred.
