# Local combined patient-summary validation

New, uncommitted frontend-only changes after Director-accepted ABG/echo source
66725cf. This summary and the qualitative-echo label clarification are not
covered by that acceptance yet. No push, merge, deployment or gate activation.

The Patient summary view brings 33 source records from the 41-item bounded state
into four panels: ABG/oxygen transport; cardiac output/pressures; echo/right-heart
findings; and perfusion/circulatory support. Other evidence remains in the library.
It preserves each source's exact values, revisions, sample/study context, methods,
time spelling, uncertainty, record status and contextual/unplaced inclusion.
It does not average cardiac outputs, select a preferred method, infer simultaneity,
calculate an integrated score/diagnosis, or issue treatment recommendations.

All summary values open the existing exact source inspector and bounded revision
history. HPI remains optional. Missing mixed-venous settings do not borrow ABG
settings; missing echo remains explicitly empty. Existing execution_enabled=false
state gating also protects the summary.

Director's nonblocking qualitative-echo wording finding is addressed in the
inspector: Recorded production tag preserves the raw value; qualitative echo
findings are explicitly source-report assertions, not directly measured diagnoses.
A focused PH inspector regression covers this presentation boundary.

Validation: 453 frontend tests passed under Node 22.13.0, typecheck and both
local/default and hosted-mode build passed, diff/whitespace passed. Exact commands,
exit codes and durations are in adjacent JSON/log files. Backend, schemas,
dependencies, migrations, database fixture, execution policy and production
configuration are unchanged; no duplicate full backend run is claimed.

Live browser: summary rendered from the actual loopback API, ABG source opened
with collection/respiratory context, exact ABG history returned one retained
revision, and PH source displayed the corrected wording. DOM and screenshot are
retained. API still reports execution disabled. All 12 tables' current row hash
matches the previously captured ABG/echo data commitment; no new execution occurred.
This row check is not a newly captured before/after history of every browser action.

The local demo remains open at http://127.0.0.1:5179/ on Patient summary. No
hosted CI, remote publication or new independent review is claimed.
