# Complete NCDC library handoff

## Requested behavior

Endocarditis was an example, not a scope restriction. Infections & treatment must expose the NCDC treatment content across all 19 clinical groups. The clinician sees the selected clinical situation, First-line treatment, Alternative treatment, Comments and Additional guidance. All source OR/PLUS choices stay inside their original column. There is no clinician-facing source-branch classification or generic withholding of a valid treatment cell.

The active AntibioticReferences wrapper mounts CompleteNcdcLibrary using ncdc-complete-guidance.json. The older curated catalogue supplies the existing group/navigation identities and the canonical acute-on-chronic osteomyelitis referral; its previous renderer and tests are retained as prior work. Old renderer verification is historical and does not establish current complete coverage.

## Source and limits

Only the retained NCDC Version 2, November 2025 PDF is used, SHA256 0debe52c37cf08dc5d112b8ef71d4ef322c323f04f712473a57a78f1bb68f90a. The complete source audit is in NCDC-COMPLETE-COVERAGE.md: 87 sections, 178 structured treatment rows, 170 outside-table notes, 174 images. All 122 discovered grids are accounted for: 109 treatment-column grids and 13 nonstandard grids shown as exact source tables in the main guidance. Twenty primary detail images also cover algorithms and defective text-layer symbols. Full original section images are separately expandable.

This preserves printed source content rather than independently endorsing its clinical accuracy. Nonstandard grids are visible source images rather than fully curated regimen fields. Genuine source anomalies remain literal with concise notes where identified; no missing units, routes, durations or weight bases are invented. NCDC says teicoplanin, not tigecycline, in the complicated endocarditis first-line OR choice. Its printed maintenance 6–12 mg lacks a weight basis, which is flagged. No JIPMER guidance, CRRT library, monographs, renal adjustment or patient prescribing is added.

## Verification and preservation

New UI tests had an observed failing run before implementation. Active production tests then navigate all 87 entries and every structured clinical row, checking that the entire first-line and alternative source cells appear in their respective panels. They also verify the severe endocarditis OR choices, component durations, chronic referral, state clearing and absence of patient storage/network writes. Separate source tests cover section boundaries, continuations, shared comments, provenance, primary fallback images and source-only identity. Logs are under ignored review-evidence/infection-library/source-corrections/complete-*.log.

The original preview at 5246 remains untouched. The candidate stays on 5247 with its existing database, signing key and browser origin. The previously served build is retained in review-evidence/infection-library/complete-ncdc/previous-build, with a file hash manifest. The launcher points to build-complete-ncdc. No data seeding or migration is performed. Mobile checks remain deferred. Final suite, review, browser and preservation results are appended after the frozen checkpoint is checked.

Independent review of fe65c2a requested three material corrections before publication. All three were reproduced by new source and active-screen regressions: MRSA cellulitis severity pairing, viral-keratitis spanning-heading context, and neonatal PDF120 private-use inequality fallback. The source projection now splits the visually verified mild and moderate/severe MRSA subrows; treats the spanning viral heading as context rather than a treatment; and supplies exact images for all detected private-use text symbols. A fourth regression prevents flattened nonstandard table text repeating its primary image. Targeted screen tests pass after the fixes. Review is a source-fidelity challenge, not clinical approval of every printed recommendation.
