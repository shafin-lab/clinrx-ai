# Antibiotic reference integration — 21 October 2026

This records the earlier reference-only import. The separate connected patient
workflow is documented in [the antibiotic workflow implementation](../antibiotic-workflow/IMPLEMENTATION.md),
with preview at http://127.0.0.1:5236/?workspace=antibiotics. The library boundary
described below is preserved.

Candidate: http://127.0.0.1:5234/?workspace=antibiotics

The antibiotics handoff is integrated as an **Antibiotic references** view inside
the existing patient workspace, alongside Patient overview, Hemodynamic review and
Kidney review. It preserves the current M7 compact row (heart rate, SpO2 only,
respiratory rate and blood pressure in the requested format) and the M8 bedside
view. It uses the same mounted workspace and patient evidence loader; browsing does
not reload M7/M8, replace their snapshots or change their session reviews.

## Imported collection and UI

- All 382 exact WHO ATC/product identities, with classification scope, combinations,
  availability limits and an explicit unlisted-medicine path.
- The 26-source core evidence library, searchable by medicine/topic, source type and
  jurisdiction. Searching does not select a different inspected medicine.
- National indication contexts, historical renal references, monitoring and explicit
  coverage states for every catalogue identity.
- Supplemental renal/CRRT cards for each identity, including the 2024 consensus
  additions for cefoperazone/sulbactam, teicoplanin and amikacin. All conflicting or
  specialist-review cards, source conditions, modality/flow/residual-function gaps,
  route/product distinctions, editions, locators and capture hashes are preserved.
- Numerical tables remain collapsed until explicitly opened. References do not
  become patient-matched regimens by opening them.
- Publisher access for Harrison’s and national surveillance links; no licensed
  Harrison/Sanford text or hospital antibiogram is imported.

The five JSON datasets were copied byte-for-byte from the handed-off prototype.
`import-manifest.json` pins their exact versions and SHA-256 values. National and
supplemental rendering components were adapted to the main TypeScript application;
no prototype dependency versions, hosting configuration or global styles were copied.
Reference code/data load in a separate lazy chunk when that view is first opened.
The source prototype and retained source libraries were not edited.

## Contract and clinical boundary

This is an isolated reference collection, not a clinical-fact owner. Imported source
records are not inserted into the patient repository or mixed with patient tests.
The reference view validates shared scope through the existing bedside model. When
patient evidence is unconfirmed, general browsing stays available and explicitly
does not claim a patient match. Exact medicine identities determine guidance;
combination or unlisted products do not inherit constituent/other-product guidance.

All imported material remains **Unreviewed, clinically ineligible and non-executable**.
The collection is withheld if an imported review/eligibility/execution flag violates
that boundary. No dose engine, CrCl calculator, patient-specific renal adjustment,
prescription, treatment selection or session-decision attachment was imported.
National/foreign source guidance does not become approved local policy.

The prototype’s separate patient cultures, antibiotic-course examples, six limited
calculator profiles and treatment-record flow remain in the prototype. They are not
connected to patient sources in this main reference view. The UI identifies that gap
and offers a return to the actual shared kidney evidence instead of manufacturing
patient context. Connecting those clinical workflows requires their own typed
source owners and validation; it is not claimed complete by this reference import.

## Verification

- **78 focused tests passed in five files**, covering the new collection/guard,
  exact identity separation, unlisted gaps, closed numerical disclosures, no fetch
  or patient write from the reference view, independent library searches, shared
  M7 session preservation, kidney navigation and existing weight/M7/M8 behavior.
- Default and synthetic RF2/authoring production builds and typechecks passed.
  Existing large-bundle advisories remain. The reference collection is a separate
  chunk, not part of the initial patient-view data load.
- All five imported datasets match their source-copy checksums. **57 retained
  captures matched**: 26 core-library texts, 29 supplemental captures and two
  national PDF captures. No source content was newly researched or reapproved.
- Real browser loaded the authoring deep link, selected teicoplanin, confirmed its
  separate national/supplemental cards and collapsed numerical tables, searched
  meropenem in the library without changing the inspected medicine, returned to
  M8, then M7 and back while retaining the reference selection/search state.
- Browser requests showed **one shared catalog GET, no other API requests**, and
  no fact revision or execution-table changes. Database integrity passed. Browser
  warning/error capture was empty. Document width matched the 390px mobile viewport;
  temporary viewport overrides were reset.
- Verification used an independent read-only backup of the synthetic candidate
  database. Its source database hash remains unchanged. The accepted checkout stays
  clean. Existing previews at 5232 and 5197 were not changed; no push/publication.

Evidence: `review-evidence/antibiotics-integration/`, including `RESULTS.json`,
`request-verification.json`, `import-manifest.json`, `source-capture-verification.json`,
`source-sha256.json`/`source-snapshot/`, `tests-corrected.log`, both build logs, DOM
captures, desktop/mobile screenshots and the verified disposable database snapshot.
Initial optional-field typing and accessible-name test failures remain in their
original logs; the corrected successful checks are separately identified.

The original handoff and prototype instructions are retained beside this document
as `PROTOTYPE-EXPORT-TO-CLINRX-MAIN-WORK.md` and `PROTOTYPE-AGENTS.md`.
