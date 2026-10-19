# Completed MAP correction → reassessment → comparison → saved handover

**Application:** b4194447829f060387b816437694af9f6c0cb60e  
**Tree:** eb6ed9d3f53727ccf186c1cb3ee5b5ba9f2677df  
**Review:** one combined captured-journey supplement; no new application increment.

M1 was independently accepted for code/evidence at evidence commit
1c7df01aa3662d15d41a325fb1808c76c85b9b33. Preserve that and C1/R1/F1/F2 closure.
This supplement does not reopen those findings or claim an independent uncoached
usability exercise. The operator completed the user-requested local synthetic actions.

## Journey and exact identities

1. **MAP correction.** fs-MAP-15 now has three immutable revisions at the same
08:15 source time on 8 October 2026: revision 1 = 61 mmHg; revision
41675deb-aa68-444f-a5fe-6ed8770c2c0c = 62.0000; revision
915ae2cb-99f9-47e6-883e-9fc51725a7f0 = 63.0000, ingestion 166.
The new revision supersedes the 62.0000 revision and preserves acquisition,
clock, quality, units and source time. The recorded reason is a transcription
correction, not a new measurement or treatment response.
2. **Separate note.** New note 00234d1d-b5ff-47da-a702-e6f50918056f/1 at
fictional case time 09:30, ingestion 167, has no predecessor. Baseline is
circulatory_cardiac/fs-CO-15/1 (4.00 L/min at 08:15); intervention is
circulatory_vasoactive/fs-N-CHANGE/1; follow-up is the exact 63.0000 MAP revision.
Actor is explicitly “Synthetic demo operator (assisted)”, not authenticated clinician
sign-off. Actual provenance authoring time remains separate from fictional case time.
Recorded findings, unconfirmed possibilities, confirmation gaps and recorded plan are
separate; no generated diagnosis or treatment recommendation follows.
3. **Comparison.** Note A is 3583c95b-119c-4daf-9642-42845112602e/1 at 09:25,
retaining MAP revision 41675deb… (62.0000). Note B is the new 09:30 note,
retaining 915ae2cb… (63.0000). Baseline/intervention references match. Both narratives
were expanded; uncertainty/provenance and complete-record disclosures remain collapsed.
The table shows retained references, not reloaded measurement values.
4. **Four-selection intermediate handover.** Added the new note/MAP to the earlier
pair, explicitly saved, reloaded and opened the saved handover. The old 62.0000 pin
returns as unavailable in the current snapshot, retaining its original digest/cutoff;
no successor was silently substituted. The earlier note and two new selections resolve.
5. **Final two-selection handover.** At the user's request, removed only the old MAP
pin and 09:25 note selection. Explicitly saved, reloaded and reopened. Final DOM says
“Restored saved handover: 2 selection(s)” and retains new note /1 and exact MAP
915ae2cb…; both retain selected cutoff 167. MAP ingestion is 166 and note ingestion
is 167. Saved timestamp displayed: 2026-10-19T11:40:55.535Z. It is a saved timestamp,
not a claim about capture time. Narrative mentions of the earlier note are retained;
that does not mean it is still a separate handover card.

## Data evidence and useful entry points

- original/map-correction/: actual before/after SQLite checkpoints (165→166),
validated-review DOM, full history DOM, two viewport JPEGs and verification output.
- original/reassessment/: actual before/after checkpoints (166→167), validated and
saved DOM, saved JPEG, original note payload, verification script/output and report.
- original/comparison/: comparison DOM and actual viewport JPEG; both note times,
IDs, exact baseline/intervention and differing MAP references are visible in the table.
- original/handover-four/: unsaved/saved/restored DOM and restored viewport images.
- original/handover-final-two/: final restored DOM and viewport JPEG. Save/removal
clicks and reload were implementation-operated; no separate final saved/pre-reload
DOM or raw storage export was captured for the removal sequence.
- exports/: all 12 tables for each of the four SQLite originals, with exact columns/rows.
Original binary bytes are also present with lossless text mirrors.

The first correction adds only one fact, one predecessor link and expected counter;
all 165 prior fact rows and both receipts are unchanged. The note append adds only
one root fact and expected counter, preserving all 166 prior rows, all links and
both receipts. The MAP-after and note-before checkpoints have equal tables/rows.
Final handover viewing has no fresh database checkpoint; those earlier checkpoints
must not be attributed to the later save/reload session.

## Runtime/build attribution and boundaries

reference/local-update/ and reference/authoring-build/ are reused evidence from the
preceding b419444 installation/readiness check, not newly captured API responses for
this journey. The verified local build requires both VITE_SYNTHETIC_HOSTED=true and
VITE_SYNTHETIC_AUTHORING=true. An initial bundle compiled with authoring alone showed
“Local authoring unavailable”; it was rebuilt with both flags before this journey.
The local-update report preserves that limitation. Earlier M1 compile success alone
was not proof of a usable runtime mode. No source changes were needed.

There are no raw browser/API request-response bodies, full authenticated network
trace or raw localStorage bytes for these actions. The captured DOM and actual
SQLite checkpoints provide the stated correspondence, not those missing proofs.
The original data verifier initially expected scope without serialized null
longitudinal_context_id; the corrected verifier checks the full scope. This was a
verification-shape correction, not an extra application save.

The publication verifier initially assumed an [expanded] snapshot attribute; the
actual DOM exports use generic disclosure labels plus rendered definition content.
The verifier now compares both full rendered narratives to their stored payloads.
This was a publication-verifier format correction, not an application operation.

No new tests, hosted CI, container/restart acceptance, delivery-fault injection,
clinical validation or independent visitor operation is claimed. Earlier 675/119
local results and 4302/668 hosted ee81661 results retain their original attribution.
General durable unsaved draft/uncertain-command recovery remains deferred; only
bounded same-browser/profile/origin handover selection recovery is exercised.

The original captures and their manifests are preserved byte-for-byte. New aggregate
hashes/exports/mirrors are publication-time artifacts, not capture-time commitments.
No ZIP or Mac access is needed. Run python3 verify_publication.py for read-only
hash/Git/SQLite/DOM checks, or recompute independently; it never starts the app,
runs application tests or executes the captured original verifier.

Please return one combined captured-journey verdict with concrete discrepancies or
scope limits. No duplicate isolated ABG/MAP walkthrough or test rerun is requested
solely for publication. The journey is assisted, so do not certify uncoached usability.
Production execution remains disabled. PR #23 application branch is unchanged;
no merge, deployment, external hosting or gate activation is authorized.
