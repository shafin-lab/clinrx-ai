# Local synthetic hemodynamics workflow milestone

## Intended use and boundary

One local synthetic patient/encounter workflow: patient evidence → exact source/history → append-only correction → separately authored reassessment → exact-note comparison → locally saved handover selection. This consolidates the existing downstream work from db56f7e through a9fffd9,26545e7,d528004 and8c7fedc with the bounded integration improvements below. It does not create a new clinical engine or establish clinician/real-patient readiness.

Production protected execution stays disabled. No merge, deployment, external hosting or execution activation is part of this milestone. Source entry is restricted to the existing opt-in IPv4-loopback synthetic authoring gateway. There is no renal, infection, respiratory-management or other new module implementation here.

## Complete bounded workflow

1. **Patient and evidence.** One verified patient/encounter snapshot supplies all views. The flowsheet retains pressure/MAP, CO/CI, rhythm, ABG, echo, infusions, fluid intervals and perfusion. All 15 evidence families remain browsable, with empty/missing families explicitly disclosed. Search uses source spelling/times, specimen and parameter context. HPI is optional.
2. **Exact inspection and history.** Inspect raw values, units, method, quality, acquisition/sample/study context, uncertainty, digest and ingestion. Revision history now shows each retained recorded result, source time, status and quality alongside its exact revision and complete disclosure. No conversion, averaging, preferred measurement, time substitution or physiological inference is added.
3. **Source entry or correction.** Six guided source areas plus clinician-authored reassessment reuse the existing strict source model; complete-source entry retains all-family access. Corrections require the exact predecessor/digest and a reason; the source time/context is retained unless explicitly edited. Review and explicit confirmation precede append. Original evidence and receipts are immutable.
4. **Confirmed-save continuation.** Find the saved record or add that exact revision to handover without re-searching manually. Both actions require the refreshed snapshot to confirm kind/ID/revision/digest; missing/mismatched confirmation withholds the action rather than substituting a successor. A failed/unconfirmed refresh blocks these actions. Start a new reassessment opens a blank assessment with no copied selections/findings; actor identity remains user-entered.
5. **Authored reassessment and comparison.** Baseline, intervention and follow-up are explicit exact references. Recorded findings, unconfirmed possibilities, confirmation gaps and recorded review plans remain separate. A new note does not revise an earlier note. Compare Note A/B explicitly, expand their authored text/caveats, and optionally add either exact selected note to handover. Accepted tuple-identity and duplicate-member protections remain unchanged.
6. **Handover.** Review source evidence and authored notes separately. Add/remove exact selections, then explicitly save locally. Reload can restore only verified exact pins from the current bounded API snapshot; unavailable/historical pins remain visible without successor substitution. Unsaved changes, storage errors and cross-tab conflicts remain explicit. A selected historical item is not presented as current.

Every workflow step has a short purpose and next-action guide. The full journey instructions are expandable. Navigation, source refresh/handoff and the finder remain guarded while an entry is unsaved, reviewed or uncertain. Keyboard focus and readable narrow-layout behavior are checked as one journey, not separately certified for every device.

## Recovery and clinical limits

A lost/malformed/unconfirmed source-save response retains the original draft/revision. Recovery uses exact lookup; absence is not rollback proof. Only an explicit retry reuses that same reviewed identity. No automatic replacement or retry, clinical execution, diagnosis or treatment advice is introduced.

Only **handover selections** have bounded browser-local storage. This is not a signed, sent, scheduled or clinically approved handover. The format stores exact references/digests/cutoffs/ingestion, not fact payloads, narratives or tokens; at most32 pins, scoped to repository/patient/encounter. Save requires storage readback. Cross-tab conflict checking is best-effort, not a transactional lock. See SYNTHETIC-LOCAL-HANDOVER.md.

General durable recovery of clinical drafts or uncertain commands after browser reload/closure remains deferred. Clearing browser data or changing browser/profile/origin can lose the saved view. These limitations must not be represented as complete clinical durability.

## Reused implementation

- Shared scope/gate/refresh boundary: usePatientEvidenceState.ts.
- Workflow routing, exact handoffs and guidance: PatientWorkspace.tsx.
- Evidence/flowsheet/summary/source/history: ComprehensiveDemo.tsx and existing evidence presentation/context components.
- Strict entry, confirmation and exact recovery: EvidenceEntryWorkspace.tsx and EvidenceEntryClient.
- Guided fields: GuidedEvidenceForm.tsx and guidedEvidence.ts.
- Exact comparison: ReassessmentComparison.tsx, evidenceIdentity.ts and retainedReassessmentReference.ts.
- Exact local selection storage/display: localHandover.ts, useLocalHandover.ts and HandoverReview.tsx.

The milestone changes presentation and integration only. Backend, schemas, policies, migrations, dependencies, fixture authoring and production configuration remain unchanged.

## Combined acceptance and validation plan

| Area | Required evidence |
| --- | --- |
| Entry/inspection | Discover and inspect pressure, CO, rhythm, infusions, gases, echo and perfusion; unknown quality/context and distinct source times stay visible. |
| Source/history | Exact source amendment retains predecessor/context; original and successor values remain readable in bounded history. |
| Reassessment/comparison | Separate original/new notes retain different exact revisions; no inherited or generated clinical conclusion. Add a selected exact note to handover. |
| Save/recovery | Confirmation before append; committed/absent/failed lookup paths preserve the exact draft and explicit retry; gate/scope/stale-response guards remain. |
| Handover | Exact selection, explicit local save, reload restoration, unavailable reference, storage failure and cross-tab conflict checks. |
| Navigation | Purpose/next step is clear; guarded drafts stay mounted; desktop/narrow/keyboard journey has no blocked required action or lost pending identity. |
| Candidate | One commit/tree; full frontend, typecheck/default/authoring builds; hosted validation for this exact candidate when available. Existing PR23 CI is not evidence for downstream source. |
| Independent review | One combined evidence index mapping final-source checks and reuse; Director records verdict and explicit remaining limits. |

Integration regressions cover the existing lifecycle plus new confirmed-save actions, stale-digest withholding, unconfirmed-refresh blocking, blank authored reassessment, comparison-to-handover and a CO-based correction/history/note/comparison/saved-handover journey. Default test timeout and assertions are not relaxed.

Use one isolated normal-flow browser-to-real-API journey with pressure/CO/infusion context and a disposable synthetic database. Preserve the earlier5193 workspace. Record original/final database correspondence, exact new records and receipts, source/build identity and screenshots/DOM with their viewport limits. Failure injection remains attributed to integration/API tests unless separately exercised live. No second ABG-only walkthrough or automatic repeat suite is required solely for publication.

## Evidence reuse and review boundaries

Prior C1/R1/F1/F2, code, Docker and lifecycle verdicts retain their exact source/scope. Accepted two-selection evidence1225b2e and three-selection evidence86aee664 establish their captured-display correspondence; they do not independently authenticate browser storage, API loading, database preservation or live gates. Separate8c7fedc/dac9fa19 timeout evidence retains its own663/17-test/typecheck attribution.

The final milestone report must distinguish fresh final-source execution from reused evidence, implementation-operated UI captures from independent usability, and actual database/API observations from DOM assertions. Do not relabel older timeout failures as proven environmental. New hosted CI must identify its actual checkout/tree. A successful local or hosted test does not imply clinical validation.

Uncoached clinician/new-visitor usability and independent Director acceptance cannot be self-certified by implementation-operated checks. Real-patient use still requires its separate identity/access/audit/storage/backup/recovery, intended-use/policy, clinical validation and governance work. No broad clinical-readiness claim follows from this milestone.
