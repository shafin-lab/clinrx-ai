# Compact reassessment comparison — source and validation review

Application: `ebbab2955109884169ae7ceef4a87d0f12af4ebf`  
Tree: `7ecf17aa1918d1267e2e00e91248b039e6632446`  
Parent: `008034ea12275406d8f5aede8ceb3aa5142570b6`

Four frontend files changed: a new read-only ReassessmentComparison, workspace integration, CSS and focused tests. Exact committed files are mirrored under source/. SOURCE-COMMIT.txt preserves raw commit bytes. Review the source through the published source tag clinrx-compact-reassessment-ebbab29; PR #23's own head remains 17e2064, so its existing CI does NOT cover this increment.

## Navigation and behavior

Explicit Note A/B dropdowns select exact kind/ID/revision tuples. No automatic original/new ordering, successor substitution, calculation, mutation, additional API fetch or protected execution is introduced. The compact table shows both note identities, source times, actor/status and all three retained stage references. Full authored narrative, uncertainty/provenance and original retained record remain expandable.

Stage references require one well-shaped stage-labelled external reference and a matching resolved exact context association in the note's encounter. Missing, duplicate, malformed or inconsistent references are disclosed. Foreign encounter notes are excluded. Reordered snapshots preserve selection; missing selected notes do not silently resolve to another. Same-note selection is explicitly disclosed. The table labels A/B rather than claiming chronology.

Reference values are not newly loaded: original ABG revision 1 may be absent from the latest snapshot, and the comparison still preserves the note's exact reference. Do not infer a new value or map an earlier reference to the latest measurement. Use earlier source history for actual measurements and context. Authored text/caveats remain source assertions.

## Captures and validation

original/README.md is the original local validation report. All 20 original manifest entries plus the manifest itself are unchanged, including initial/final build bytes and logs. Capture-time no-publication wording applies to the implementation stage only; this publication now exposes the same bytes.

- original/frontend-tests.log: 602 frontend tests, 18 files, --maxWorkers=2, 34.78s. This is implementation-produced execution, not Director's rerun.
- original/default-build.log and original/final-authoring-build.log: final typecheck/default and local authoring builds pass. Existing bundle warning remains.
- Focused 26-test result is implementation-reported; no separate raw focused log was saved in this package. The focused assertions are included in the full suite.
- Initial new-test failures were corrected for fixture aliasing/query typing. No original raw initial-test log was saved. They are disclosed in the original report; do not invent independent reproduction evidence.
- Full-suite execution preceded a final CSS-only fix for inherited table min-width. Final builds and captured browser layout cover the final CSS; this is not a claim of a clean-archive/full-suite run after that fix.
- original/source.json hashes all four final files; they match committed bytes. No new hosted CI, backend test or container acceptance is claimed.

The new local authoring build on 5191 was installed while preserving the prior build and database. original/comparison.txt retains explicit selections and disabled-execution text. original/comparison.jpg shows both note columns and their different follow-up ABG revisions in one table. Full narratives remain collapsed; this is NOT both complete narratives simultaneously visible. Captured layout: viewport 431x823, table width365, top31.84375/bottom809.4375, page/document width431. These measurements are implementation-reported; no separate original layout JSON was saved. Image filename matches JPEG bytes. General device, pointer/touch and accessibility certification are outside scope.

Note A: abae4ef7-74c4-48cc-bb50-f50e9fb151cd/1, 09:50 UTC, follow-up ABG 1c1f16d9-33d7-40fb-a94f-013a383c9bfc revision1. Note B: 90c89b62-1f3a-4903-b10d-eb8c6711e921/1, 09:55 UTC, same ABG identity revision aeaca128-a674-4dfa-859a-9ab11d2a9368. Baseline/intervention are unchanged. Earlier evidence supplies the persisted pH 7.3300/7.3500; this view does not newly load those measurements.

## Preservation and portable access

Actual before-view/after-view all-table row exports are equal: 174 fact revisions, both retained receipts, all original notes and references unchanged. No new SQLite database file/checkpoint was captured in this task. TABLES-INDEX.json adds readable per-row exports; column labels come from the earlier preserved database schema, not a new schema probe/checkpoint. Earlier actual DB evidence remains separate at c967cc2521131606e54cc90322154a7aa93e2f2e:
https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6252257278

MIRRORS.json supplies bounded, lossless base64 text parts for large/binary files. PUBLICATION-SHA256SUMS.json covers publication files; verify_publication.py is stdlib/data-only and does not run application or tests. No ZIP or Mac access is needed.

Preserve Director acceptance of e1b60bb596fcdf5f0c8a29bd331f8d135f45851c captured comparison, c967cc saved-note evidence, prior walkthroughs and R1/F1/F2 closure. This new four-file UI increment requires its own bounded review and is not automatically accepted by those verdicts.

Durable browser-session recovery remains deferred. Production connected execution stays disabled. No merge, deployment, external hosting or gate activation is authorized or performed. No clinical-readiness claim follows.
