# Patient antibiotic workflow

This opt-in loopback candidate documents manual antibiotic source assertions in the
existing M6 repository. Keep prescriptions, completed administrations and non-delivery
separate. No medication is physically administered or sent to an external prescribing
system. Do not make the unreviewed reference JSON executable or inherit its dose tables.
The separately maintained renal-dose candidate profiles may show source-matched adult
suggestions only for exact supported identities, indications and renal-support settings.
They are external guidance for clinician review, not local policy or validated treatment.
Keep provenance visible, hold ambiguity and scope gaps, and never turn a suggestion into
an order without explicit user action and completion of the source record review.

Use the shared patient snapshot and one repository cutoff. Culture review must retain
exact specimen/isolate/AST provenance and hold incomplete, intermediate, resistant,
ambiguous or conflicting results. Source-reported susceptibility is not a validated
regimen. Never invent missing patient demographics, allergies, doses or cultures.

Cockcroft–Gault is explicit adult arithmetic with selected inputs and renal-context
limitations; it cannot substitute for CRRT clearance. Use it only when a matching
non-dialysis profile requires stable CrCl. HD/CRRT use their own explicitly matched
support-specific source rows and must not derive a dose from Cockcroft–Gault. Preserve
source values and fail closed for unsupported modalities, unstable function, missing
clinical context, unclear flow or incompatible cultures.

Validate/review/save manual records, preserve source-owned corrections and exact
history, and look up an uncertain save before an explicit retry. Pending recovery is
versioned and repository scoped; preserve malformed or concurrent recovery bytes.
Keep production routes and live data unchanged.
