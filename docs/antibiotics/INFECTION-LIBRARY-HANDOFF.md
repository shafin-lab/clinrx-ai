# NCDC-only infection library — handoff

The user removed the supplemental institutional policy source on 25 October 2026. NCDC is now the sole infection-library source. The previous combined-source checkpoint remains in Git history at `ec853a2`; its served build is retained under ignored `review-evidence/infection-library/ncdc-only/previous-build/`.

## Latest source corrections

[Current preview](http://127.0.0.1:5247/?workspace=antibiotics&antibioticView=library&reviewBuild=ncdc-corrections) includes the targeted corrections to NCDC sections1.1/10.1/10.2 and paragraph reflow. See [NCDC-SOURCE-CORRECTIONS.md](NCDC-SOURCE-CORRECTIONS.md) for source scope and remaining ambiguities. One selected source option is displayed at a time; uncertain branches are readable with explicit clarification warnings. Chronic guidance uses the existing acute record after selecting the applicable clinical pattern.

Final checks: 1,540 frontend tests passed / three skipped; parser regression passed; typecheck and production build passed. Independent review approved the bounded corrections, and its minor wording issue was removed. Browser checks and unchanged original/candidate database hashes are recorded in the correction ledger. The prior source-removal record below is historical; its assertion of unchanged NCDC entries applies to that removal step, not these later targeted corrections.

## Preview and scope

[Antimicrobials → Reference library](http://127.0.0.1:5247/?workspace=antibiotics&antibioticView=library&reviewBuild=ncdc-only).

The original preview at port 5246 is separate and unchanged. The updated port 5247 uses the same copied synthetic database. Browser-only notes remain in their existing origins. No patient records, prescriptions or review notes are changed by this source removal.

The active catalogue has 19 clinical groups, 87 NCDC infection entries, 210 clinical contexts, 115 selectable source options and 119 held contexts. All pre-existing NCDC source objects, groups, infection objects, clinical contexts, treatment text and identifiers match the previous checkpoint exactly. Withdrawn-source-only infections and appended contexts are removed. The source registry, UI, generator and published PDF assets are NCDC-only. Related entries and comparison notes are also removed from the retained legacy supplemental data.

**At the source-removal checkpoint**, endocarditis, the chronic reference and paragraph formatting were unresolved. The later targeted corrections above address those reported workflows. Genuine source ambiguities and other uncurated contexts remain; complete clinical-content validation is not claimed. No automatic source-reference resolution, dose calculation or prescribing is added. CRRT and monographs remain deferred from this library.

## Verification record

Removal checkpoint: `8654a70d4024d8a197bb4460aa72787e48a265cd`.

- Full frontend run: 1,534 passed, 3 skipped; 66 passed files / 2 skipped; exit 0 with maxWorkers=2. Focused regressions: 51 passed. Initial removal tests: six expected failures before implementation.
- TypeScript `tsc --noEmit`, production build, deterministic generator `--check`, shell syntax and whitespace checks passed. Existing large-chunk build warning remains.
- Independent read-only review of `ec853a2..8654a70` approved the bounded removal with no Critical/Important findings. Reviewer verified exact preservation of NCDC objects, rejection of other sources and no dangling legacy supplemental source IDs. This approval does not certify clinical-content completeness.
- Published build text/assets contain no withdrawn-source references. Removed PDF returns HTTP404; retained NCDC PDF returns HTTP200. Browser verified NCDC-only labels, seven respiratory entries, two urinary entries, CAP display and reload. No patient save was performed.
- Original and copied patient database hashes match the pre-removal baseline, pass integrity check, and retain 209 fact revisions / four existing commands. All 14 original preservation-manifest entries remain unchanged.
- Mobile checks deferred. Backend code unchanged; backend suite not rerun for this source-removal change.

Evidence: `review-evidence/infection-library/ncdc-only/` includes the new regression RED/GREEN logs, NCDC before/after comparison and database baseline hashes. Full NCDC source/hold inventory: [INFECTION-SOURCE-MAPPING.md](INFECTION-SOURCE-MAPPING.md).

## Relaunch

After building the NCDC-only frontend into `review-evidence/infection-library/build-source-corrections`, run `sh tools/launch_infection_library_preview.sh`. It binds only loopback port 5247 and requires the prepared copied database and adjacent signing key. Do not restart or replace port 5246.
