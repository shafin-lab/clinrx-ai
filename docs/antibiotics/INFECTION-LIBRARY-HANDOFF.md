# Infection library checkpoint — 25 October 2026

Implemented in `codex/infection-library-20261025`, based on the served `9909e23` checkpoint. Implementation commits: `b741f31`, `a3b8245`, `98cf6ce`. No merge, push, original-preview replacement or patient save was performed.

## Open the candidate

[Antimicrobials → Reference library → Infections & treatment](http://127.0.0.1:5247/?workspace=antibiotics&antibioticView=library&reviewBuild=infection-library).

The original preview remains on port **5246**. The new origin uses a byte-identical copy of its synthetic database. Browser-only M7/M8/M9 review notes remain in their original origin; they were not migrated to port 5247. No browser storage was cleared or copied.

The active library replaces medicine classification browsing with the 19 NCDC clinical groups. Choose an infection, clinical situation and, where the source offers safe alternatives, one treatment option. Only the selected source guidance is displayed. NCDC owns overlapping contexts; named JIPMER additions retain their own provenance. No cross-source dose assembly, patient dose adjustment, prescription action, monograph section or CRRT reference is added.

Prior reference UI and data remain preserved, including the old component as `LegacyAntibioticReferences.tsx`; the active library does not mount it. Existing cultures, prescriptions, renal review and other clinical workspaces retain their existing implementation.

## Content coverage and limits

- 19 clinical groups; all 87 named NCDC subsections; 105 infection entries.
- 248 clinical contexts; 125 selectable source options; 148 contexts have no selectable regimen and explicitly require source review.
- All 77 numbered JIPMER disease rows are accounted for in the crosswalk, together with unnumbered gastrointestinal pathogen tables. Accounting for a row is not full treatment transcription or clinical validation.
- Complex neonatal/age-dependent combinations, conditional or ambiguous source cells, and unresolved cross-references remain held. Original text and PDF locators are retained. Some treatment durations remain in source notes rather than promoted into a fixed duration field.
- Missing routes, units, components and durations are never guessed. Source unit anomalies and the unidentified extra 500 mg in small-intestine prophylaxis are held. Blank-dose urology rows remain visible as holds.
- Lung-abscess duration is explicitly shown as the source-confirmed 4–6 weeks. Endocarditis uses a neutral infection title with empirical/definitive distinctions in context labels.
- Both full source PDFs are retained locally with hashes and page links; publisher links are also available. Source identity is frozen and does not imply that later publisher revisions were checked.

This is an **unreviewed, non-executable reference preview**, not a clinically approved prescribing library or hospital policy. Detailed coverage, source ownership and every held context are listed in [INFECTION-SOURCE-MAPPING.md](INFECTION-SOURCE-MAPPING.md).

## Verification

- Full frontend suite: **1,534 passed, 3 skipped**, 66 passed files / 2 skipped, using `vitest run --maxWorkers=2` from `frontend/`; exit 0.
- Focused source/UI/model/legacy/shared-workspace regression set: **51 passed**; exit 0. New review regressions were observed failing before correction.
- TypeScript `tsc --noEmit`, reviewed production build and generator `--check`: exit 0. Existing large-chunk warning remains.
- Independent review of `9909e23..a3b8245` found two Important source issues. Re-review of `a3b8245..98cf6ce` confirmed both resolved, with no outstanding Critical/Important findings for this bounded read-only checkpoint. This is code/source-transcription review, not clinical approval.
- Browser: 19 groups, CAP outpatient/ward contexts, replacement of complete source options, unmatched-search clearing, JIPMER perinephric-abscess provenance, culture review, existing prescription records, patient overview, return to library, and deep-link reload verified without saving. Final build's patient endpoints returned HTTP 200; both retained PDFs returned HTTP 200.
- During initial preview setup two patient requests returned 500; subsequent reloads and the reviewed-build run returned 200. No backend code was changed and the initial cause was not established. Backend full suite was not rerun for this frontend-only change.
- Original served build, original database and a pre-existing uncommitted navigation patch: all 14 preservation-manifest entries unchanged. Original and copied SQLite files retain SHA256 `cb3d6abdad8b3f91fd32a1eeca7890917e8cfb08c34f5fbcceae0283a22c0b14`, pass integrity check, and retain all 14 table counts, including 209 fact revisions and four existing commands.
- Mobile checks deferred as requested. Other previously stopped workflow changes are not included.

Ignored local evidence is under `review-evidence/infection-library/`: full suite, focused RED/GREEN, build/typecheck, deterministic check, preservation manifest, database-copy ledger and final pneumonia screenshot. Runtime database/key remain outside source control in `runtime/infection-library/`.

## Relaunch

Keep the prepared database, adjacent signing key and reviewed build. From this worktree run:

```sh
sh tools/launch_infection_library_preview.sh
```

The launcher binds only `127.0.0.1:5247` and checks that the prepared store/build/key exist. It does not copy, seed or migrate the original database. Stop only this candidate process before relaunching; leave the original port 5246 process running.

To rebuild the static catalogue, use the Python runtime with pdfplumber and the frozen read-only evidence paths described by the generator; run `--check` to compare deterministic output. Build the frontend with the same synthetic hosted, RF1, RF2, authoring, weight-entry, antibiotic and M10 feature flags enabled. Clinical execution remains disabled.
