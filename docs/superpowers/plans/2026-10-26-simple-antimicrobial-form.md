# Simple Antimicrobial Form Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, TDD and one fresh fixed-checkpoint reviewer.

**Goal:** Apply the approved four-field form without altering clinical data or review semantics.
**Architecture:** Adapt the existing editor and compatible manual chart DTO; retain exact old serialization and recovery. Optional details compose a validated schedule.
**Tech Stack:** React/TypeScript, Pydantic, existing loopback preview.
**Spec:** docs/superpowers/specs/2026-10-26-simple-antimicrobial-form-design.md

## Global constraints
Preserve sources/, original databases, open browser drafts, previous assets, source provenance, saved reviews, prescribed-vs-given separation and explicit validate/review/save. No profile changes. Mobile deferred.

## Tasks
- [x] 1. RED→GREEN backend optional preparation/basis and prescription detail coherence/legacy exact serialization; regenerate transport. Tests: tests/test_antibiotic_chart.py.
- [x] 2. RED→GREEN combined dose parser, frequency custom fallback, timezone adapter; implement simpler editor and migrate existing user-facing tests. Tests: simpleAntimicrobialForm, antibioticWorkflow, antibioticCorrections, prescriptionChart.
- [x] 3. Full frontend/backend suites, typecheck/build; one independent reviewer at code checkpoint. Fix material findings with regressions. Copy-only browser save/recovery/history and preservation verification.
- [x] 4. Archive existing builds, publish compatible assets/backend to existing ports without data migration; open a fresh preview tab and record handoff.

## Review focus
- Missing preparation must remain unknown; linked administrations must preserve exact source product identity.
- Unsupported dose text must not silently assume units or numeric amount; given/non-delivery remain separate.
- Corrections preserve source-owned basis, candidate receipts, custom frequency and exact pending recovery.
- Local date/time conversion must preserve instants including DST-invalid entries and unchanged legacy seconds.
- Optional detail text must roundtrip without duplicate append or schedule disagreement.

## Ledger
Baseline 2135531; existing feature checkout reused, only untracked frontend/node_modules present. Explicit implement approval covers the demonstrated design; no additional approval gate needed. Task 1 DTO consumed by Task 2 editor and transport; optional fields must be omitted on legacy requests to preserve canonical receipts. Task 3 consumes Task 1/2 release; no original patient writes.

Tasks 1 and 2 complete at 902f105. Backend 2 new regressions RED→GREEN, focused frontend 82 passed. Initial full frontend 1675 passed/3 skipped. Maintained backend run pending. Bare pytest collected a PDF-import helper unavailable in the backend venv; that helper passes separately (1 test) using the bundled PDF runtime with the existing pytest path, without package changes.

Independent read-only checkpoint review (2135531..902f105): one P2, repeated DST local time silently chose earlier occurrence. Fixed with regression against actual checkpoint source RED→GREEN: reject ambiguous new entries with actionable exact-offset fallback; edits on the same source day preserve the recorded offset. Exact offset source entry stays inside Source details. No other findings or deferred minors.

Final: fixed DST repeated-time finding — recordForm DST subprocess regression against checkpoint source RED→GREEN; current typecheck clean. Full frontend post-fix run: 1679 passed, 3 skipped; a final added exact-offset calendar validation test also passes in the 15-test helper/form run. Final release suite will include it. Browser copy save succeeded with blank preparation, explicit combined 500 mg, Every 12 hours, duration/review and instructions; no administration inferred.
Own final workflow check: switching from a prescription with lengthy optional instructions to Held incorrectly validated the now-hidden prescription schedule length. Regression RED→GREEN; only prescription mode validates that length. Held retains null amount/unit/basis/schedule and no prescription metadata. No new clinical logic.
Final frontend release: 1681 passed, 3 skipped; TypeScript clean; production build passed with the existing chunk-size warning. Isolated database counts differ from the original fictional demo by exactly one new prescription; all other fact counts, including administrations/non-delivery, are unchanged. Reload restored the prescription and optional fields; Cancel released all navigation. Original four databases remain SHA256-identical and integrity-check clean.


## Final handoff
- Code commits: 902f105, 8846984, e1090e2. All existing work retained; no sources/ edits.
- Final verification: 1681 frontend tests passed, 3 skipped; 4540 maintained backend tests passed. The separate PDF importer test passed (1) using the bundled PDF runtime and existing pytest; no dependencies installed. Typecheck, production build and git diff --check passed. Existing chunk-size and Starlette deprecation warnings remain.
- Independent checkpoint review: DST ambiguity P2 fixed with regression. No deferred review findings. A further non-delivery hidden-field regression was fixed and verified.
- Isolated browser verification: optional preparation left blank; combined dose and explicit frequency saved, reloaded and restored for correction. Optional duration and instructions preserved; actual history untouched. Cancellation released navigation. Exactly one prescription appended to isolated verification.sqlite3, no other fact-count change.
- Existing preview ports 5247, 5249 and 5251 updated additively, backends restarted using original signing keys and database paths. Their original HTML/assets and backend files remain under review-evidence/simple-antimicrobial-form-20261026/previous-*. Original 5246 untouched. No data migration, seed, patient write or browser-review rewrite.
- All four original patient databases remain byte-identical (SHA256) and integrity-check clean after restart. Preserved original tabs, including the existing unsaved draft; opened a fresh final tab, inspected the new form, cancelled without saving. Navigation available. Temporary verification server stopped. Mobile deferred.
- Preview: http://127.0.0.1:5251/?workspace=antibiotics&antibioticView=patient&reviewBuild=simple-form-e1090e2 . Main workspace: port 5247, same path. Select Add antimicrobial to open the new form.
- Deliberate scope: this release applies the approved prescription form. The separately discussed age-only shared context entry is not changed; existing DOB-derived source facts remain preserved. Treatment start remains unknown unless source-recorded; the date picker accurately labels the prescription/event timestamp. No new clinical dosing profiles.
