# Bounded M6–M10 correction design

Execution authority: the user's 25 October instruction to proceed with the bounded pass recommended in the independently reviewed research. This document concretizes that approved scope; it does not expand the clinical roadmap. Research: `/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/connected-overview-candidate/review-evidence/m6-m10-architecture-research-20261024/RESEARCH.md`.

## Intent and chosen approach

Make M6–M10 feel like a continuation of one patient review. Automatically display relevant recorded evidence, remove redundant expanded result blocks, preserve the evidence behind calculations and drafts, and make review/reload behavior consistent. The user selected the recommended bounded integration approach over display-only cleanup. A universal source graph, service rewrite and all-specialist completion gate are outside this pass.

Worktree: `/private/tmp/clinrx-bounded-m6-m10-20261025`, branch `codex/bounded-m6-m10-20261025`, base `8263db838ea1f2fd11bbb9783470ad2102990c6f`. The app worktree tool could not resolve the project mirror as a Git repository; a separate Git worktree was created from the verified integration repository. Main work's original layouts and the original integration checkout remain unchanged.

## Binding constraints

- Preserve all existing work, patient data, source bytes/digests/revisions, correction history and origin-local review history.
- Keep ports 5243, 5244 and 5245, their served builds, databases and signing material unchanged. New preview uses a copied synthetic database, separate build and loopback origin on port 5246 if free.
- Relevant records appear automatically. No generic reuse button, second source write, or repeated entry to display existing evidence.
- Avoid redundant expanded copies of values within one active results region. Preserve legitimate serial tests, cross-system context, summaries, trends and source/history inspection.
- Blood products remain visible and counted through the existing `input_blood` owner/link. Do not alter product/fluid arithmetic, create intake from viewing M10, or add a linked M10 volume again.
- Keep clinical execution disabled, M7-C gated, reference JSON unreviewed/non-executable, all dosing formulas/rows unchanged, and source/calculation eligibility qualifications intact.
- Do not mutate historical canonical payloads through new default model fields. Optional additions must retain the old canonical serialization when absent; test this explicitly.
- No live hospital integration, external order, remote push/merge or clinical activation. Mobile and M11 are deferred.

## A. Exact evidence and renal review

Use the existing exact identity helpers and a small shared component-key function, including repository, kind, ID, revision and component ID. Digest disagreement for an identical identity is a conflict; equal numeric values across distinct sources remain distinct. Avoid a universal alias registry.

M8 investigation buttons carry exact source keys/group rather than a free-text query. The source drawer opens exactly those counted contributors, including BUN-only labels and urine components. Other exploratory searches remain available. Total calcium uses its supported mapped concept. Ionised calcium without a verified systemic/post-filter role is displayed as site-unresolved; do not invent a site from proximity or a generic label.

Carry report and record status plus source flags into M8 component display. A final-but-invalid source is visibly invalid. Preserve pending/withdrawn/superseded evidence and do not certify usability from report finality.

Give M8 the same stable scope/coverage/exact-pin evidence identity as M7/M9, including all contextual evidence actually shown as review context. Use the same matcher in M8 and overview, and recheck the latest rendered identity after acquiring a save lock. Retain old notes as historical legacy evidence; do not delete or silently upgrade them. A separate daily-fluid window remains explicitly outside that review unless already attached; do not enlarge the scope silently.

## B. One transfusion read scope

The shared patient loader retrieves M10 once for the exact confirmed RF2 repository/watermark/window and supplies that result to both overview and M10 detail. Failure in M10 does not erase independently confirmed M7/M8/M9 evidence; it blocks M10 actions and labels the M10 read unconfirmed. No unbounded stale fallbacks.

Extend `M10Transport.catalog(start,end,scope?)` with optional `{repository:string;cutoff:number}` for compatibility with standalone unit clients. The synthetic gateway accepts the paired repository/cutoff, rejects mismatched repository, negative/future cutoff and partial pairs, and reads at that bounded cutoff. Unknown-availability terminal corrections at the chosen cutoff still withhold older positive claims and remain visible for reconciliation. Corrections committed later cannot leak into an earlier snapshot.

Expose the shared read as `{snapshot?:M10Snapshot;loading:boolean;error?:string}`. A supplied shared read disables component-owned catalog fetching; standalone component use may retain its current transport fallback. Save/refresh invalidates the shared loader once, not a second closure-captured refresh. Keep existing matching, history, recovery, interpretation and accounting gates.

M10 laboratory projection uses complete component identity and typed known concepts where available; unknown original labels remain inspectable and legacy display matching stays conservative. Do not drop distinct same-ID cross-kind evidence or count the same exact component twice.

## C. Respiratory support-to-ABG first slice

Keep original respiratory records and import/correction APIs. Introduce a pure evaluation resolver, not another saved analyzer report. It may supply **missing FiO2 only** from one exact linked support record when all of these hold: same confirmed patient/encounter/repository and selected cutoff; exact linked kind/ID/version resolves to one current recorded, usable support source; exact known-instant support acquisition equals gas collection time; the gas explicitly confirms settings at sample; and there is exactly one compatible usable FiO2 measurement. Keep its full source pin in calculation inputs. Own-record FiO2 always retains precedence, including its unusable state; never replace suspect/invalid local values with a nearby better-looking value.

Any unresolved link, mismatched time, later setting, superseded revision, unknown timing, ambiguous/multiple source, invalid units/role/quality or unconfirmed sample settings withholds the dependent calculation with a precise reason. No nearest-time/last-observation-carried-forward rule. Display relevant support sources automatically even when ineligible. Historical sample choice is a normal viewing operation, not reuse.

Add a versioned, non-executable mode reference registry for VC–AC/VC-CMV, PC–AC, SIMV variants, PSV, CPAP, PRVC and APRV; show source mode wording and profile-specific parameter hints, with unknown/custom mode preserved. Keep interface/NIV, HFNC and configured versus measured values separate. Recognition supplies semantics only; it never chooses settings or establishes device equivalence. Resistance may recognize an explicitly supported conventional VC acquisition label, while retaining passive/occlusion/constant-flow gates. Mixed/adaptive/unknown modes do not inherit that permission.

For generic minute/alveolar ventilation, add minimal optional acquisition metadata for breath channel and averaging/acquisition identity to the source measurement contract. New metadata is source capture, not inferred from mode. Omitted fields must serialize exactly as before. Generic measured Vt and RR without compatible explicit channels/acquisition remain visible but the product estimate is withheld. Exact matching total or spontaneous channels with compatible interval/acquisition may calculate; mixed mandatory-Vt/total-RR cannot. Set targets never substitute for delivery. Preserve all other formula coefficients, ranges and withholding rules; increment the calculation version for changed eligibility.

Use one primary gas table. The selected-sample panel shows support/source context and calculation outputs; move its repeated full measurement list behind source details. Preserve requested ABG/PFT columns and omitted raw history. Remember an explicit selected sample across reload by exact source identity and evidence scope; stale selection is labelled historical/unconfirmed rather than silently choosing the newest gas. No observation or review is saved by navigation/selection.

The finite first slice does not pair chemistry/CO or introduce full support episodes, PFT/SBT lifecycle, device control or new diagnoses. Relevant chemistry/CO remain automatically visible context. Those larger clinical relationships follow separately.

## D. Antimicrobial continuity without broader prescribing

Keep the four-input CrCl form and all separate renal-support/dose safety controls. Automatically populate only unambiguous supported recorded creatinine and recorded weight from the confirmed snapshot, with source/time visible and explicit source-unit conversion where supported. Do not select a dosing-weight source, infer age/coefficient or substitute a CRRT metric. Never overwrite a manual edit or a stale calculation silently. Ambiguous/ineligible values remain visible context and hold automatic input selection. Confirmed source changes invalidate the calculation/suggestion; user-entered hypothetical values stay local calculator inputs and do not create measured records.

Carry a typed, bounded dose-review provenance object from a suggestion to the manual prescription draft and its retained request metadata: profile version/source, the four arithmetic inputs, calculated CrCl if applicable, selected renal/dialysis context, culture/empiric basis and evidence scope/source pins when used. Label it candidate decision context, not a server-validated regimen. Keep user-edited final medication fields distinct from the original suggestion. Corrections retain original context; fresh manual records have none. Preserve canonical/retry compatibility for historical requests with no added field, all request size limits, and exact AST validation. Do not add new numerical dose content.

Automatically show relevant recorded prescription/administration and culture context together. Call it recorded therapy; current-treatment lifecycle remains unconfirmed because local order authoring lacks broader stop/hold states. Do not make that lifecycle a hidden scope expansion.

## E. Presentation and recoverable saves

Preserve the compact M7 vital row and existing BP/echo work. Collapse duplicate detailed vitals/timeline/MAP presentations only where the active view repeats the same values without a distinct task. Keep original-source and trend access available and keyboard-operable. Shared context stays available automatically; details can be progressively disclosed without another reuse action. Correct stale “session-only” review copy.

M10 unsubmitted session draft reads must distinguish absent, valid and damaged bytes. Damaged bytes remain retained and block overwriting/new submission until an explicit safe discard; pending submitted commands continue their existing separate exact-request recovery. Recovery cannot cross repository/patient/encounter, record owner or correction predecessor. A stale-evidence draft remains recoverable but cannot be submitted as current without renewed source review. Do not convert saved receipts to failed saves because refresh failed.

## Verification and independent ownership

Each task has a failing behavioral regression before its fix, appropriate focused checks, and a fresh task reviewer. No concurrent application implementers. Main work is consulted for ownership/constraints; its generic old-task replies are not new ownership acceptance. Root coordinates the isolated branch and shared integration.

At the final commit run frontend suite with four workers, backend suite with repository path configured, typecheck, seven-flag production build to a new immutable directory, and whitespace checks. Populate only a disposable copy on 5246. Exercise cross-view navigation, one-source automatic visibility/no duplicate rows, exact source links, corrected/qualified cases, ABG/support transition, culture/draft provenance, save/reload, and linked blood remaining counted once in daily balance. Recheck original manifests and all three existing preview databases/builds. Bind source/build/test/browser evidence to the frozen commit; a fresh whole-branch reviewer independently challenges it. Resolve important findings before delivery. Clinical readiness remains separately gated.

## Builder's discretion

Use existing React/TypeScript and Python/Pydantic patterns, no new dependencies. Exact names for small pure selectors, test fixture construction and text layout are implementation choices. A new global graph, general inference engine, content ingestion pipeline or clinician governance dashboard is not a reasonable interpretation of this design. Any necessary compatibility ruling must be recorded in the execution ledger.
