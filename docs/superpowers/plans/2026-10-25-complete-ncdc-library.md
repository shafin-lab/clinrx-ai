# Complete NCDC Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for this approved continuation. Steps use checkbox syntax.

**Goal:** Reflect all NCDC disease-group treatments in Infections & treatment, including first-line/alternative cells, conditions, comments and algorithms. The user explicitly rejected clinician labels such as source branch; endocarditis was an example, not the scope limit.

**Architecture:** Preserve the existing curated catalogue and work. Add a faithful, complete projection of all 87 NCDC clinical sections using original table cells, section notes and exact cropped section images. Render one clinical context at a time with First-line treatment, Alternative treatment and Comments, preserving NCDC OR/PLUS choices rather than inventing combinations. Complete source images remain available for audit and display algorithms where structured rows are unavailable. No patient writes or dosing inference.

**Tech Stack:** React/TypeScript, Vitest, Python pdfplumber/pypdfium2, existing preview gateway.

**Spec:** User corrections in this chat, including 12:05 screenshots: severe endocarditis First line is vancomycin+meropenem OR teicoplanin+gentamicin, with source doses/stages/durations; no source-branch jargon. NCDC only. All19groups, not only endocarditis.

## Constraints and review focus
- No JIPMER, CRRT library, monographs, patient writes, or original5246 preview replacement.
- Preserve complete original source wording and provenance. Teicoplanin is the printed drug, not tigecycline. Never infer the missing maintenance /kg.
- Distinguish first-line and alternative columns. Preserve route OR choices and component durations. Do not interpret adjacent drug lines as new combinations.
- Do not silently omit conditional or multiline rows; retain exact source images and coverage records for unusual tables/algorithms.
- Reflow PDF soft line breaks while preserving standalone OR, PLUS and deliberate clinical grouping.
- No duplicated doses across main display and source-image evidence by default. Source images can be expanded separately; algorithms without structured rows must be visible in the main experience.
- Chronic acute-on-chronic referral must display the existing acute source content in place after choosing the applicable acute context, without copying patient values.

## Ownership / interface
Source agent owns NEW tools/build_ncdc_complete_library.py, NEW frontend/src/infectionLibrary/data/ncdc-complete-guidance.json, frontend/public/assets/infection-sources/ncdc-sections/, NEW tools/test_ncdc_complete_library.py, NEW docs/antibiotics/NCDC-COMPLETE-COVERAGE.md. Parent owns new React/model/tests and active wrapper, launch/build/handoff. No shared-file edits.

Projection schema: {source:{id,name,version,url,sha256},sections:[{infectionId,section,name,pdfPages,rows:[{id,label,firstLine,alternative,comments,pdfPages}],notes:[{text,pdfPages}],figures:[{imagePath,pdfPage,caption}],sourceText}]}. IDs match existing ncdc-X-Y infection IDs. Notes are outside the structured table cells, not repeated table text. Figures may be all exact section/page crops for full audit; parent avoids rendering duplicate tables by default.

### Task1: Complete source projection
- [ ] Source agent writes failing coverage/content tests; extracts all rows/alternatives/notes and crops all section segments with exact heading boundaries.
- [ ] Verify every section, source identity, page continuation and fallback coverage; commit only owned files.

### Task2: Clinician display
- [ ] Parent writes failing pure component/model tests for native/prosthetic/severe endocarditis full firstLine OR/PLUS content, alternatives, no source-branch labels, source warnings, state resets and chronic reference.
- [ ] Implement CompleteNcdcLibrary with existing19group navigation and selected clinical row, source-first labels, readable paragraphs/operators and source provenance.
- [ ] Activate via existing AntibioticReferences wrapper once projection is ready. Retain previous curated component/tests as preserved work. Verify active shared-workspace integration.

### Task3: Review and publication
- [ ] Freeze checkpoint, independent full-change review, correct material findings.
- [ ] Run complete frontend suite, source tests, deterministic generator, typecheck, production build.
- [ ] Back up current5247build; publish new build at5247 using unchanged database. Browser verify multiple groups, source alternatives, source algorithms, chronic reference, source links and reload; no saves.
- [ ] Verify source/build/database preservation; update coverage ledger honestly and show preview.
