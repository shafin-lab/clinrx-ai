# Supplementary infection evidence

The user approved the expandable design and implementation on 25 October 2026. NCDC remains the primary source. Its treatment records, source cells, comments, figures, reference relationships and PDF are unchanged. The new `Further evidence & alternatives` disclosure follows the NCDC source area, begins closed, and closes again when the infection or clinical situation changes.

## Scope

Thirteen distinct entries use nine canonical sources dated 2023–2026. Source versions are explicit; access dates do not qualify an old guideline as recent. Sources are linked rather than downloaded by the browser. Clinical-context entries are labelled separately from dosing references. All content is general reference material, with its own population, source location, rationale, difference from NCDC and limits.

| NCDC section | Supplement |
|---|---|
|1.1|ESC organism/valve context; teicoplanin label and adult sepsis infusion context only in the severe-sepsis row|
|5.2 and18.6|One shared IDSA cUTI duration/context entry, with study exclusions and severe-CAUTI limitations|
|6.1|NACO herpes-specific genital-ulcer option|
|6.2|NACO external-wart local treatment option|
|6.4|NACO candidiasis-specific vaginal-discharge option|
|6.6|NACO Table3.5 intact PID regimen|
|6.9|NACO Table3.3 uncomplicated NG/CT urethral regimen|
|9.7|IWGDF/IDSA soft-tissue duration versus bone-infection context|
|13.2|WHO respiratory-diphtheria treatment/antitoxin context|
|16.1|SDCEP acute periodontal regimen in gingivitis/periodontitis rows only, with the narrower indication explicit|
|17.4|EBMT adult severe mucocutaneous/visceral HSV regimen in the BMT-HSV row only|

Other infections keep their existing display; no empty supplement or generic substitute is added. Earlier literature, access-limited dosing claims, CAP population mismatches, uncertain neonatal boundaries, JIPMER, CRRT and full antibiotic monographs remain outside this release. Previously recorded NCDC extraction/display issues are not silently repaired in this supplement task.

## Files and checks

`supplementaryCatalogue.ts` stores source identities once and binds distinct entries to exact infection/row IDs. `SupplementaryEvidence.tsx` renders native details/summary with no data entry, prescribing controls, patient calculations, fetches or storage writes. The existing renderer adds this component after NCDC source details; only its introductory description changes to explain the separation.

Focused checks passed16tests, including seven browser-component tests and three catalogue-contract tests. The full frontend suite passed1,561tests with three existing skips across two skipped files. Typecheck, separate production build and whitespace checks passed. The build retains a large-chunk warning. No backend code changed or migration ran.

Evidence lives under ignored `review-evidence/infection-library/supplementary-evidence-20261025/`: baseline377-file hashes, RED/GREEN logs, full suite, typecheck/build logs, frozen review hashes and preservation checks. Production output is separate at `review-evidence/infection-library/build-supplementary-evidence-20261025/`. The previous served candidate build is retained in the evidence directory's `previous-build/`.

Both candidate/original databases retain SHA256 `cb3d6abdad8b3f91fd32a1eeca7890917e8cfb08c34f5fbcceae0283a22c0b14`, pass integrity check, and retain209fact revisions/four command rows before publication. Original port5246/build/signing material and synced `sources/` remain unchanged. Keep the current candidate origin5247 so existing browser review storage is retained. Mobile checks remain deferred.

Independent review of all six frozen source/test files found no blocking or material issues. It spot-checked the teicoplanin, NACO PID/urethral, EBMT HSV, SDCEP and SSC content against supporting sources. It did not constitute clinical validation or an independent full-text reread of every source; source retrieval limits are retained in the review report. The teicoplanin “Updated 10 March 2026” label is the emc hosting date; its text revision is 2 December 2025. Both meet the recent-source boundary. This optional metadata precision does not change dosing or applicability.

Desktop browser checks remain the publication gate. Native disclosure behavior and mobile behavior were not exercised by the reviewer; the implementer verifies desktop and mobile remains deferred. Clinical suitability for any individual patient is outside this general reference feature.
