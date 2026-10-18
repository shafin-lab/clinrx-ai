# Local synthetic hemodynamics consolidation

Base: `db56f7e8164a7a3c46c6c8e17a56c0d9088c2de5`. This bounded increment connects existing evidence browsing, inspection, correction/history, authored reassessment and comparison, adding a session-only handover selection review. It introduces no clinical interpretation rule, backend contract, migration, dependency or execution activation.

## Workflow and reusable components

The opt-in local authoring build opens one patient/encounter workspace. `usePatientEvidenceState.ts` owns the shared bounded snapshot, verifies scope and disabled execution, and rejects stale refresh results. `PatientWorkspace.tsx` keeps the viewer/editor mounted and coordinates exact source handoff, guarded navigation, comparison and handover.

`ComprehensiveDemo.tsx` reuses the existing flowsheet, summary, source inspector, history and retained-result examples. `EvidenceEntryWorkspace.tsx` reuses guided forms, strict source validation, immutable append, exact lookup and explicit same-revision retry. `ReassessmentComparison.tsx` and the accepted C1 retained-reference decoder are unchanged. `HandoverReview.tsx` retains selected exact source bytes, repository and cutoff and marks unconfirmed historical selections; it does not substitute successors or save/send a handover.

Recorded assertions, authored assessments and retained derived examples stay labelled separately. Missing/unknown source context is not confirmation. A transcription correction does not establish a new measurement, physiological improvement or treatment effect.

## Affected files

- `frontend/src/App.tsx`: selects the consolidated workspace only for the existing loopback-only authoring mode.
- `frontend/src/demo/usePatientEvidenceState.ts`: shared scope/gate/refresh boundary.
- `frontend/src/demo/PatientWorkspace.tsx`: workflow shell and exact handoffs.
- `frontend/src/demo/ComprehensiveDemo.tsx`: optional embedded/shared mode and inspector actions; standalone defaults remain.
- `frontend/src/demo/EvidenceEntryWorkspace.tsx`: shared snapshot, exact handoff, mounted-draft guard and stale-history rejection.
- `frontend/src/demo/HandoverReview.tsx`: read-only session selections and exact retained references.
- `frontend/src/demo/evidenceEntry.css`: responsive shell and comparison selectors.
- `frontend/tests/patientWorkspace.test.tsx`: integration acceptance cases.
- `tools/run_evidence_entry.py`: local launcher description.
- `.github/workflows/ci.yml`: bounded-concurrency frontend suite and authoring build/log; no execution or deployment job.

## Acceptance cases and evidence reuse

Fourteen new integration cases cover shared loading; exact predecessor handoff; draft retention; committed/absent/failed recovery without automatic retry; gate and patient/encounter mismatch; historical handover selection; stale history/handoff rejection; correction-to-new-note comparison/handover; disappeared-note disclosure; and confirmed save with failed refresh. Existing comparison/C1, guided entry, transport and full-fixture suites remain in the frontend suite. Focused authoring/gateway/storage tests cover unchanged real API boundaries.

Earlier Director acceptances remain evidence of their original source and captured scope, not of this candidate: R1/F1/F2 on `008034e`; C1 on `db56f7e`; local update evidence `32fe43410b4a5061ce8649094e2edd6cda55b11c`; and previous Docker/lifecycle scopes. The accepted reference database is copied for an isolated normal-flow browser exercise, leaving the original workspace unchanged. New candidate validation is reported separately.

## Remaining integration boundaries

- Obtain hosted CI for the exact chosen candidate/tree when separately authorized; PR #23's old CI does not cover this source. Local checks use Node 24.12.0/npm 11.6.2; hosted pins remain Node 22.13.0.
- Independent review and an uncoached new-visitor workflow test remain. Implementation-operated desktop/narrow captures are not independent usability or accessibility certification.
- Save uncertainty/failure paths have integration/API coverage; the new normal-flow browser exercise is not live fault injection or a complete network trace.
- Drafts, comparison and handover selections are in memory. Durable recovery across reload/closure remains deferred; unresolved pending saves must use the existing exact recovery path before leaving.
- Handover is review-only, with no durable handover, recipient, sign-off, scheduling or transmission workflow.
- Container acceptance remains attached to its previous source; no new container build is claimed here. No renal, infection, respiratory or other module integration is included.

Production protected execution remains disabled. This is a synthetic local prototype, not clinical readiness or authorization to merge, deploy or host.
