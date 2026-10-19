# Hemodynamics milestone completion summary

Updated 19 October 2026.

The local synthetic hemodynamics workflow is implemented and validated at
`b4194447829f060387b816437694af9f6c0cb60e`, tree
`eb6ed9d3f53727ccf186c1cb3ee5b5ba9f2677df`. Director has accepted the M1
code/evidence correction and the completed assisted journey within their stated
scopes. Exact-candidate hosted CI has passed. Independent uncoached usability
remains unfinished; these acceptances do not establish clinical readiness.

## What is complete

One patient/encounter workspace connects evidence browsing, exact source inspection,
append-only correction/history, separately authored reassessment, comparison and
explicitly saved local handover. The base ICU fixture contains 156 current records
across 14 populated families; 15 families are supported and HPI remains optional.
The current authoring episode also contains the later corrections and notes; its
snapshot count is not the original 156-record fixture count.

The completed assisted journey corrected the 08:15 MAP to 63.0000 mmHg while retaining
61 and 62.0000 in history. A separate 09:30 synthetic reassessment pins that exact
MAP revision, 08:15 cardiac output 4.00 L/min and the noradrenaline change. The 09:25
note retains its 62.0000 reference. Both notes can be compared without rewriting
either. After explicit removal of the older handover pair, reload restores exactly
the corrected MAP and the 09:30 note. Removing selections does not delete facts.

Director verified the captured journey, original artifacts, four SQLite checkpoints,
readable exports, exact references and record/receipt preservation. The correction
and note append add only their documented facts, link and counters. Database
checkpoints are attributed to those appends, not the later handover sessions.

## Accepted evidence and exact candidate CI

| Item | Result and boundary |
| --- | --- |
| M1 correction | Accepted: repository/scope changes reset comparison choices; saved-result continuation preserves repository identity; pending requests remain mounted. |
| Completed journey | Accepted, bounded captured-evidence scope; assisted operation, not independently witnessed or uncoached usability. |
| Exact b419444 hosted CI | Run 39260359954, attempt 1: SUCCESS. Both raw logs identify this exact checkout, not a merge or the old PR head. |
| Backend | 4,302 passed, one existing warning; 1,038.00 seconds. |
| Frontend | 675 passed; typecheck, standard build and synthetic authoring build passed. Both required synthetic build flags were enabled. |
| Environment and schema | Python 3.11.6, Node 22.13.0, npm 10.9.2; dependency consistency passed, migration head m7_0008. |
| Earlier results | Local 675/119 checks and earlier ee81661 hosted 4,302/668 keep their separate attribution. They are not substitutes for the new exact-head CI. |

- [Exact-candidate CI results on PR 23](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6268381652)
- [Hosted run and job logs](https://github.com/shafin-lab/clinrx-ai/actions/runs/39260359954)
- [Completed journey evidence and combined review scope](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6266492469)
- [M1 correction evidence](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6263860148)

## Remaining boundaries and next decision

No remaining required correction was identified in the supplied M1 and captured-journey
verdicts. The exact-candidate CI attribution gap is now closed. No more isolated
ABG/MAP walkthroughs or repeat suites are needed merely to repackage this evidence.

The unfinished usability criterion must remain explicit. If needed before product
acceptance, run one user-led task and fix the concrete obstacles, rather than
repeating an assisted demonstration and calling it independent usability. This
need not prevent preparing the next synthetic workflow specification.

General durable recovery of unsaved drafts/uncertain commands remains deferred.
Saved handover is bounded to the same browser/profile/origin. No newest-authoring
container acceptance, authenticated real-patient use, clinical validation or external
hosting approval follows. Real-patient identity/access, audit, storage/backup/recovery
and clinical governance are separate prerequisites for real-patient use, not
requirements to start a local read-only synthetic planning increment.

The proposed next step is RF1 in RENAL-FLUID-WORKFLOW-SPEC.md. It needs explicit
implementation authorization after specification review. New additions stay frozen
until then. Production protected execution remains disabled; no merge, deployment,
external hosting or execution activation is authorized. PR 23 remains draft/open
at its unchanged application branch; this document does not change that branch.
