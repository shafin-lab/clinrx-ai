# RF2 urine fluid and weight workflow specification

Draft for Director review, 19 October 2026.

Application baseline: `5cb73212ae6104b02bad361886cd9507795d88bf`.
Application tree: `7505ff88af8089f2d729fc230b15f3a604c5c9c0`.
RF1 specification: `7fa529dd276ceb140700760a358cf3493b44e85b`.
RF1-F1 accepted correction evidence: `39e4f51ffdcac868d676a2e7b85d0fefd7be945c`.

RF2 completes one local synthetic journey: record urine, fluid and weight evidence → inspect sources → append a correction → author a renal/fluid reassessment → compare retained notes → explicitly save and restore a handover. It contributes to M8 renal physiology and renal support and M9 fluid balance and output, without renumbering or completing either module.

This is a specification only. Implementation requires approval of this exact revision and user authorization. Production clinical execution remains disabled. Merge, deployment, external hosting and container replacement are excluded.

## Outcome and milestone boundary

An adult synthetic patient has one repository and encounter shared by renal/fluid and hemodynamic views. A nurse-facing charting path records what was measured or reported; a clinician-facing path records an authored assessment and review plan. Recorded evidence, clinician-authored assertions and retained derived examples remain visibly distinct.

RF2 ends with one integrated candidate, one combined validation package and one Director review. It does not require separate ABG/MAP demonstrations, a new inference engine or completion of every renal feature. A reviewer must be able to follow the entire journey without oral instructions; any implementation-operated journey is labelled assisted, with an uncoached attempt reported separately.

## Included and deferred work

| Included | Deferred |
| --- | --- |
| Urine volumes with explicit source intervals, missing amounts and collection context | Calculated urine rates, mL/kg/h, AKI detection/staging or oliguria alerts |
| Documented oral, enteral, IV and blood-product intake; drain/other measured losses; recorded CRRT net removal | Fluid prescriptions/orders, pump integration, administration verification, nutrition composition and blood-bank fulfilment |
| Measured and reported weight, with asserted purpose, method and source time | Calculated weight change, ideal/adjusted/dry weight, BSA and weight-driven treatment rules |
| Original and corrected evidence with exact history; typed withdrawn/invalid circulatory records remain inspectable | Generic creatinine authoring or new typed specimen/quality/withdrawal fields in ClinicalObservation |
| Source-reported interval/cumulative totals and balances as separate reported assertions | Generated totals/balance, conversion, interval prorating, gap filling or automatic duplicate reconciliation |
| Renal/fluid reassessment with explicit evidence selections, optional intervention context and recorded review plan | Diagnosis generation, causal attribution, response classification, treatment recommendations or scheduled actions |
| Exact mixed-kind inspection and bounded saved local handover | Cross-device synchronisation, shared multi-user handover, clinical sign-off and general durable draft/command recovery |

The fluid form does not create an infusion order. An entered volume describes documented intake or output, not proof that a prescribed amount was delivered. CRRT removal is context only; RF2 does not prescribe modality, dose, anticoagulation or treatment settings.

## Existing contracts and proposed representation

Reuse immutable facts, repository transactions and existing correction rules. Do not extend legacy clinical models, introduce a new fact kind, change production routes or create a competing renal record. Product DTOs and generated transport schemas may be additive and local-only.

| Entry | Existing storage and proposed local convention |
| --- | --- |
| Urine/fluid amount | CirculatoryEvent.recorded_amount retains the exact decimal string and raw unit; recorded_interval retains source start/end assertions. Missing amount is null with an explicit source reason. Recorded zero remains a quantity. |
| Chart category | A versioned local source code distinguishes urine, oral/enteral/IV/blood intake, drain/other loss, CRRT net removal, reported total and reported balance. Existing source codes retain their meaning. |
| Weight | A separate CirculatoryEvent amount in a weight category, with no interval. Measured body weight, reported weight and existing dosing weight remain different source assertions. A dosing-weight record is not relabelled as a measured daily weight. |
| Collection and method context | A bounded versioned product metadata entry in existing external_evidence, plus readable source description. Its fields are source assertions, not new generic clinical fields. |
| Renal/fluid note | A distinct local renal_reassessment source marker on CirculatoryEvent, authored narrative, exact resolved context associations and bounded versioned evidence-pin metadata. No fabricated intervention is required. |
| Existing creatinine | Read-only ClinicalObservation with its existing concept, value, time, conflict and uncertainty fields. No new specimen, quality, collection-time or withdrawal semantics are inferred. |

Use a new local namespace, provisionally `clinrx.local.renal-chart/v1`, and separate metadata/note namespaces. Publish the strict metadata DTO and serialization rules in the implementation review. Required fields: category, amount state (recorded or missing), missing reason when applicable; optional source-asserted collection/method, device/site identifier and weight purpose. For reported totals/balance, retain the source calculation/completeness limitation. Unsupported metadata stays unavailable. Metadata must agree with the stored amount, interval and category; reject contradictory representations.

Product metadata is encoded in one explicitly identified existing SourceCode entry, not parsed from free prose. Enforce one entry, an exact supported version, bounded canonical JSON, exact keys/types and duplicate-member rejection before interpretation. Narrative is display text, never the authority for quantity, interval or reference resolution. Preserve raw metadata even when its version cannot be interpreted; withhold unsupported structured actions.

Structural unit checks use an explicit local allowlist: volume mL or L; weight kg or g. Signed amounts are allowed only for source-reported balance categories. Other entered amounts must be nonnegative. These are chart-shape constraints, not physiological ranges. Unlike source units remain separate; there is no conversion. Existing historical records with other units remain inspectable without being silently normalised or coerced into these entry forms.

If the proposed metadata cannot fit existing bounded SourceCode and fact limits, or existing repository semantics cannot preserve it losslessly, return a specification amendment before coding a clinical-model or storage redesign.

## Charting and correction workflow

1. Open Renal and fluid review for the shared patient, encounter, window and cutoff. Choose Record urine, Record fluid or Record weight. These are local synthetic actions, distinct from clinical execution.
2. Show required fields beside the entry: source category, quantity or explicit missing state, raw unit, source time/interval assertions, actor and uncertainty. Unknown context must be selectable; no positive-quality, verified-clock or measured-status defaults.
3. Urine/fluid records use an explicit interval or a clearly marked point event. Partial or unknown bounds remain partial/unknown and are not turned into an hour. Reject contradictory exact start/end ordering using the accepted exact-time machinery; do not round timestamps or guess local timezone. Do not calculate duration or rate. Weight uses its own point/unknown time and explicit measured/reported/dosing purpose; measurement method may be unavailable.
4. Present a validated review showing scope, proposed exact identity, amounts, intervals, raw context and limitations before the explicit save. Validation is not a saved confirmation.
5. Save one immutable fact. Confirm only after exact response/digest/ingestion correspondence. Refresh failure after a confirmed save must retain that confirmation and block unsafe continuation until scope is reconfirmed.
6. Correct from an exact selected revision. Retain kind/ID and original content, append a new revision with actor, reason and exact predecessor digest. Preserve unrelated fields. A changed interval/amount is a transcription/source correction unless explicitly authored otherwise; it is not a new measurement or physiological improvement.
7. Reject stale, foreign-repository and conflicting predecessor submissions. Do not rewrite history or automatically rebase a correction onto a successor. A genuinely new collection uses a new fact identity.

RF2 adds no mass edit, automatic correction, automatic withdrawal or source deletion. Existing typed withdrawal/invalid statuses remain visible. Generic laboratory historical status is never interpreted as withdrawal.

## Reassessment and comparison

The renal/fluid note requires a review question, recorded findings, unconfirmed possibilities (including explicit none recorded), confirmation gaps and a recorded next-review plan or explicit unscheduled state. Actor identity remains an unauthenticated synthetic assertion. No action is scheduled by saving the plan.

Select one to twelve exact evidence items. The selectable read set is allowlisted: urine/fluid/weight/support chart events, existing creatinine observations and relevant existing hemodynamic evidence already available in the composite. Label references as reviewed evidence, with optional earlier/later/intervention context. No intervention is compulsory and selection order does not establish chronology or causation. Resolved context associations and the retained pin metadata must agree exactly; repeated or ambiguous role entries fail closed.

Each pin retains repository, patient/encounter, kind/ID/revision, canonical digest, ingestion identity and original selection cutoff. At save validation, resolve the exact historical revision in that repository, verify full correspondence and ensure it existed at its declared cutoff. A selected withdrawn/invalid/conflicting item remains explicitly labelled as such and cannot become an unqualified measured finding. A source change after selection prompts review; never silently select its successor. The user may explicitly retain the historical selection with a visible disclosure.

Create a new reassessment when reviewing corrected evidence; earlier notes and their references remain untouched. Compare two exact renal notes and their retained references, without calculated deltas or preferred/latest selection. Generalize the source-reference adapter explicitly for the allowlisted ClinicalObservation and CirculatoryEvent representations; do not cast a laboratory item to CirculatoryItem. Preserve C1 duplicate-member rejection and R1 tuple identities, including IDs containing delimiters or escaped characters.

Use bounded exact lookup/history for references absent from the terminal snapshot. A valid superseded revision is not automatically unavailable because a successor exists. If exact resolution cannot be confirmed within limits, retain the pin as unavailable with a reason; never substitute another revision. Typed source withdrawal, note retention and applicability for a new clinical inference remain distinct concepts.

## Saved local handover

Introduce an additive version 2 saved format for the allowlisted mixed-kind selections. Retain version 1 storage keys, bytes and decoding unchanged. If only v1 exists, offer an explicit copy into v2 after valid scope checks; no automatic migration, merge or overwrite. If both exist, identify each and ask the user to choose the saved set. A failed copy leaves v1 intact. Saving v2 never modifies v1.

Every pin includes exact reference/digest/ingestion, original selection cutoff and repository scope. Restore after disabled-gate confirmation and exact resolution at the pin's historical cutoff; preserve original values and notes even when successors exist. Show superseded/withdrawn or unavailable status explicitly. No raw signed context, request command or access secret is saved to localStorage.

Keep existing bounds of 32 pins and 131,072 serialized characters or stricter shared limits; reject oversized data, duplicate keys/members, malformed pins and unknown versions without clearing stored bytes. Mixed selections share retrieval and response budgets; bounds failure does not imply complete restoration. Source facts remain in the repository, not copied into a second browser record store.

Require explicit save/update/remove actions. Display unsaved changes and restored timestamp; removing a pin deletes no clinical fact or note. Preserve conflicting-tab detection and storage failure handling. Removing an unavailable pin requires an explicit action. Scope replacement clears active selections synchronously but retains pending original requests and historical confirmations; never resolve repository A's saved reference against repository B.

Saved selections survive supported reloads in the same browser. Unsaved notes and uncertain commands do not gain durable recovery in RF2. Warn against reload/closure while completion is uncertain; do not claim that saved handover makes pending writes recoverable after closure.

## Local API and safety boundaries

Extend only an explicit opt-in loopback RF2 gateway. Preserve RF1 read/history routes and guards. Add strict RF2 validation, save and exact-lookup DTOs scoped to the fixed synthetic encounter and allowed categories; do not widen generic clinical authoring or expose arbitrary facts. Existing hemodynamic entry remains separate. Production/Docker defaults and clinical execution routes stay unchanged.

Reuse transaction-safe append/idempotency behavior: retain the exact pending request and request bytes in memory. After lost, malformed or post-commit failure responses, block replacement save and navigation that would lose the request; exact lookup first. A matching retained result is returned unchanged. Absence is not rollback proof; explicit retry reuses the identical original request and identity. No automatic retry, new UUID, rebasing or replacement. Invalid input must fail before writes and errors must not expose internals.

Capture one cutoff for composite reads. Validate repository/patient/encounter, window/profile/limits, assembly digests, exact facts and ingestion throughout; retain RF1-F1 complete selected-history correspondence. Existing aggregate row/history and response-size limits apply across creatinine, chart records, note references and handover lookups. No cap increase, unbounded resolver or partial-success display masquerading as complete data.

## Proposed implementation files

Paths below are planned, not changed by this document. New names may be consolidated during implementation, but a wider clinical-contract/migration/inference change requires a specification amendment.

| Files | Intended change |
| --- | --- |
| backend/app/api/schemas/renal_fluid_entry.py (new) | Strict chart/note metadata, drafts, validated/saved replies, historical pins and mixed reference resolution DTOs |
| backend/app/services/renal_fluid_entry_service.py (new) | Category admission, correspondence, exact pin verification, correction and retained lookup using existing transactions |
| backend/app/demo/renal_fluid_entry_gateway.py (new) | Separate opt-in loopback RF2 routes; fail closed and disabled execution |
| backend/app/demo/renal_fluid_fixture.py | Explicit disposable RF2 fixture composition; no seed/reset at startup or modification of accepted datasets |
| backend/app/services/renal_fluid_product_service.py; api/schemas/renal_fluid.py | Bounded mixed reference read/history if required; preserve original RF1 transport and history semantics |
| frontend/src/api/renalFluidEntryClient.ts; renalFluidEntryTypes.ts; renalFluidEntryDecoders.ts (new) | Strict local write/lookup and mixed resolution boundaries; generated additive transport schemas |
| frontend/src/demo/RenalFluidEntryWorkspace.tsx; RenalFluidReassessment.tsx; renalFluidEvidence.ts (new) | Guided chart forms, exact review/save/recovery, explicit mixed evidence adapter and renal note comparison |
| frontend/src/demo/RenalFluidReview.tsx; PatientWorkspace.tsx; chartEntries.ts | Visible entry/inspection navigation, new local chart categories, shared state and return focus |
| frontend/src/demo/renalFluidHandover.ts (new); HandoverReview.tsx; useLocalHandover.ts; localHandover.ts | Versioned mixed handover alongside unchanged v1 compatibility; no silent migration |
| tools/export_renal_fluid_transport.py | Additive schema generation/drift checks, without silently expanding existing response unions |
| tests/test_renal_fluid_entry.py; test_renal_fluid_entry_gateway.py; frontend/tests/renalFluidEntry.test.tsx; renalFluidReassessment.test.tsx; renalFluidHandover.test.tsx (new) | RF2 cases and integrated storage/transport/UI coverage |

Reuse existing exact identity, retained reference decoder, transaction/recovery and provenance helpers. Keep the hemodynamic editor mounted across navigation/scope changes. Shared components may gain explicit adapters; existing hemodynamic semantics and tests must remain intact.

## One synthetic case and acceptance cases

Use a disposable copy of the accepted shared episode, preserving its original rows and two retained receipts. Add fixture examples explicitly before validation: documented intake, zero/missing urine, gap/overlap intervals, measured versus dosing weight and a source-reported balance. These are test assertions, not treatment thresholds. No real patient data or existing user's database is modified.

| Case | Required outcome |
| --- | --- |
| RF2-01 shared scope | One repository/patient/encounter/cutoff. Replacement repository, patient or encounter clears choices; mounted drafts and pending requests retain original identity. |
| RF2-02 charting | Save urine, fluid and weight records through real API with exact decimals/units, source time/interval, purpose, method/unknown context and actor. Show confirmed ingestion distinctly from validation. |
| RF2-03 missing and context | Zero versus missing, point versus interval, unknown/reversed/ambiguous bounds, unlike units and measured/reported/dosing weight stay distinct. No generated totals/rates or physiological interpretation. |
| RF2-04 correction | Correct one recorded urine/fluid amount and one weight assertion. Exact original bytes/history remain; unrelated fields persist; stale/wrong-repository predecessor fails without writes. |
| RF2-05 reassessment | Save a renal note without a forced intervention, referencing corrected chart evidence and existing creatinine. Exact persisted pins, digests, associations and narrative correspond. |
| RF2-06 comparison | New note uses corrected evidence while earlier note retains its original revision. Duplicate JSON members, collisions, missing/foreign refs and digest/ingestion contradictions withhold exact-reference claims. |
| RF2-07 historical handover | Save mixed selections, reload, resolve exact historical revisions even with successors, remove one pin, explicitly save and reload. Old notes and source facts remain untouched; unavailable pins are retained visibly. |
| RF2-08 compatibility | v1 remains readable/byte-preserved; explicit v1→v2 copy and both-present choice work. Unsupported versions, corrupt/oversized storage, conflicting-tab and quota failures do not silently overwrite data. |
| RF2-09 uncertain save | Exercise post-commit lost/malformed delivery and pre-dispatch absence separately. Same request retained; exact lookup then only explicit identical retry. Pending editor survives refresh/scope changes without auto-save. |
| RF2-10 bounds and isolation | Combined lookup accounting and size caps apply. Wrong scope/cutoff/window/digest/ingestion fails closed; stale history cannot resurrect; no arbitrary fact access. |
| RF2-11 execution and preservation | Preparation/new clinical execution remain rejected. Writes equal only declared new records/revisions/notes and expected links/counters; both original receipts and all unrelated rows remain byte-identical. |
| RF2-12 coherent use | Complete chart→correct/history→reassess→compare→handover/reload on desktop and a recorded narrow viewport, with understandable errors, keyboard navigation, focus and contained scrolling. Record assistance and uncoached difficulties accurately. |

## Combined validation and Director review

Freeze one final application candidate. Run targeted API/storage/decoder/UI cases and affected RF1-F1, M1, C1/R1, hemodynamic entry/recovery and handover regressions. Run full backend/frontend suites, typecheck, schema drift checks and default plus explicit RF2-enabled local build once after substantive integration is complete. Obtain hosted CI for that exact candidate with actual checkout and enabled-build flags recorded. Unchanged suites need no repetition solely for evidence publication; do not relax assertions/timeouts to obtain a pass.

Capture one real-API synthetic journey covering all three chart forms and representative corrections, the two notes, comparison and save/update/reload handover. Save exact source/build identities, relevant browser DOM/screenshots, redacted API bodies and before/after SQLite checkpoints plus all-table exports. Capture relevant localStorage bytes before save, after save and after reload to establish the mechanism beyond identical DOM text. Preserve sensitive contexts separately; published copies redact signing material/tokens and state the resulting attribution limits.

Validate original/terminal fact identity, canonical digests, repository/scope, original selection cutoffs, ingestion bounds, note-reference correspondence and exact pending request equality. Database differences must match a declared write ledger; read/restore/history/recovery lookup intervals add no facts or receipts. Fault injection occurs only in the isolated harness, with dispatch/commit/delivery boundaries disclosed. It does not activate clinical execution or establish real network-loss behavior.

One indexed review package contains START-HERE, the candidate/diff, case matrix, exact commands/versions/exit codes, raw final and failed logs, before/after data, captures, manifests and portable data-only verification. Originals remain unchanged. Link it from PR #23 without a ZIP when publication is authorized. Prior RF1/hemodynamic acceptance supplies unchanged invariants only, not new RF2 runtime/compatibility proof.

Director's requested decision is approval or required corrections for this specification first; implementation acceptance is a later single combined milestone verdict. Stop for amendment if clinical model/storage redesign, new calculations or production access is required. Independent uncoached usability, authenticated users/roles, patient matching, backup/recovery and clinical validation remain later real-patient gates.

## Hospital adaptability and later renal work

ICU, HDU and ward use the same source model with different display density and locally agreed documentation frequency. RF2 does not hard-code a universal shift boundary, monitoring interval, escalation threshold or international hospital policy. Local policy mapping and clinician/nurse usability review precede any hospital deployment.

Later work can separately specify laboratory authoring, broader electrolytes, calculated accounting, governed AKI detection/staging and full renal-support prescription/delivery. None is implicitly approved by RF2. No AI interpretation, renal prescription or execution gate is enabled here.
