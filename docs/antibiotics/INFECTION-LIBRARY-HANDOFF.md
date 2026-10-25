# NCDC-only infection library — current checkpoint

The user removed the supplemental institutional policy source on 25 October 2026. NCDC is now the sole infection-library source. The previous combined-source checkpoint remains in Git history at `ec853a2`; its served build is retained under ignored `review-evidence/infection-library/ncdc-only/previous-build/`.

## Preview and scope

[Antimicrobials → Reference library](http://127.0.0.1:5247/?workspace=antibiotics&antibioticView=library&reviewBuild=ncdc-only).

The original preview at port 5246 is separate and unchanged. The updated port 5247 uses the same copied synthetic database. Browser-only notes remain in their existing origins. No patient records, prescriptions or review notes are changed by this source removal.

The active catalogue has 19 clinical groups, 87 NCDC infection entries, 210 clinical contexts, 115 selectable source options and 119 held contexts. All pre-existing NCDC source objects, groups, infection objects, clinical contexts, treatment text and identifiers match the previous checkpoint exactly. Withdrawn-source-only infections and appended contexts are removed. The source registry, UI, generator and published PDF assets are NCDC-only. Related entries and comparison notes are also removed from the retained legacy supplemental data.

**Known defects remain:** NCDC endocarditis combinations are held rather than fully curated; the chronic osteomyelitis reference to acute osteomyelitis is unresolved; extracted PDF line breaks still affect prose display. This removal does not fix those problems or imply complete clinical-content validation. No automatic source-reference resolution, dose calculation or prescribing is added. CRRT and monographs remain deferred from this library.

## Verification record

Final verification for this removal is recorded below after checkpoint review and preview checks. The older combined-source full-suite result is historical and does not establish correctness of this change.

Evidence: `review-evidence/infection-library/ncdc-only/` includes the new regression RED/GREEN logs, NCDC before/after comparison and database baseline hashes. Full NCDC source/hold inventory: [INFECTION-SOURCE-MAPPING.md](INFECTION-SOURCE-MAPPING.md).

## Relaunch

After building the NCDC-only frontend into `review-evidence/infection-library/build-ncdc-only`, run `sh tools/launch_infection_library_preview.sh`. It binds only loopback port 5247 and requires the prepared copied database and adjacent signing key. Do not restart or replace port 5246.
