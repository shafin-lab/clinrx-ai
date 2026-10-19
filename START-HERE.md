# Hemodynamics workflow milestone — one combined review

**Candidate:** ee81661d7ae70d6ab5491a2da8634f675381d00a  
**Tree:** d5b2b74af2ded0b78bc1cb25037391083eba24e5  
**Immediate parent:** 8c7fedc6db110747966488fbe52bd5815c7c5713  
**Consolidated review baseline:** db56f7e8164a7a3c46c6c8e17a56c0d9088c2de5

This is one local synthetic workflow milestone and one Director review request. It does not implement a new clinical engine, approve real-patient use, activate production execution or authorize merging/deployment. PR23 remains draft/open at17e2064; review this tagged candidate, not the old PR head.

## What is now connected

Patient/encounter → all-family evidence/ICU flowsheet → source context and readable original/corrected history → strict source entry/correction → separate clinician-authored reassessment → exact-note comparison → explicitly saved local handover.

The final nine-file increment adds purpose/next-step guidance, exact confirmed-save continuation, a blank new reassessment action, comparison-to-handover actions and readable history values/times/status/quality. The consolidated range from db56f7e spans21 files and also includes shared scope/gate state, exact handoffs, guarded mounted drafts, source-time finding and bounded local handover storage. Those intervening features need consolidated code review; accepted viewing supplements do not automatically approve all their implementation.

BP/MAP, CO/CI, rhythm, ABG/sample context, echo estimates, infusion documentation, fluid intervals and perfusion remain distinct recorded evidence. All15 families remain browsable; this fixture contains14, with HPI explicitly optional/absent. No averaging, preferred CO, dose conversion, carry-forward, generated diagnosis, physiological relationship, causal response or treatment recommendation is added.

## Final-source execution results

| Check | Result | Evidence |
| --- | --- | --- |
| Local full frontend | 668 passed /21 files;43.01s test-run duration | original/frontend-full.log; wrapper elapsed time is recorded separately in checks.json |
| Local typecheck/default/authoring builds | Passed | original/checks.json and individual raw logs |
| Focused integration/entry/comparison/guided checks | 94 passed /4 files,14.80s; before the final type-option cleanup | original/focused-initial.log; final full suite includes these assertions |
| Hosted exact-candidate CI | SUCCESS, run39218687969, workflow_dispatch | original/ci-result.json; original/ci-complete.log |
| Hosted backend | 4,302 passed; one existing warning;713.90s | Full backend suite in original/ci-complete.log |
| Hosted frontend | 668 passed, typecheck, default and authoring builds passed | Same raw CI log |
| Schema/dependencies | CI checks passed; migration m7_0008 | Same raw CI log |
| Data-only journey verification | PASS | original/journey-verification.json; original/verify_journey.py |

Both hosted jobs check out **ee81661 itself via its source tag**, not a synthetic merge. The Git tree is d5b2b74. Hosted Node22.13.0/npm10.9.2/Python3.11.6 remain distinct from local Node24.12.0/npm11.6.2. Existing backend deprecation and build-size warnings remain nonblocking. No duplicate suite was run solely to publish this package.

Initial668-test success was followed by a TypeScript error from an unsupported query option in one new test. The option was removed; the final full suite/typecheck/builds then passed against matching committed bytes. Initial logs and hashes are retained separately. No timeout or assertion was relaxed, and older unrelated timeout causes are not relabelled.

## One browser-to-real-API journey, not another ABG exercise

A fresh expanded synthetic database and the exact authoring build run only on127.0.0.1:5195. The existing5193 workspace was not the target. Source metadata/build hashes, actual served-body hashes and browser-observed asset paths correspond; this is implementation-produced correspondence, not authenticated proof of every resource load.

1. Opened the workflow guide and integrated all-time flowsheet. Pressure, flow, rhythm, gas, echo, infusion, fluid and perfusion sections remain available with distinct source timing/quality.
2. Authored original note **f01d969c-54a5-4566-815e-2bd8ae5e9505/1**, ingestion163, explicitly selecting CO fs-CO-15/1, noradrenaline event fs-N-CHANGE/1 and original pressure fs-MAP-15/1.
3. Found the08:15 mean arterial pressure, reviewed61mmHg and appended correction **41675deb-aa68-444f-a5fe-6ed8770c2c0c**, ingestion164, recording62.0000mmHg. Original acquisition, clock, quality, units and source time remain unchanged; only result/provenance/correction fields change. Both values appear in real bounded revision history.
4. Used confirmed-save actions to select the exact corrected pressure for handover. Started a blank separate reassessment; no evidence or authored findings were preselected/copied.
5. Authored new note **3583c95b-119c-4daf-9642-42845112602e/1**, ingestion165, retaining the same CO/intervention and exact corrected pressure. The earlier note still references pressure revision1. Findings, possibilities, confirmation gaps and an unscheduled recorded plan remain distinct.
6. Compared both notes, expanded authored narrative/provenance and used Add Note B to handover. Saved two exact selections once and reloaded; both returned with their original digests/cutoffs/revisions. The corrected pressure pin retains selected cutoff164; the new note pin retains cutoff165. Neither is silently rebased.

The external ASGI wrapper only observes the real gateway; it does not replace results or inject faults. Accepted request bodies and response bodies are retained, with signed state_context values redacted where present. Headers and query strings are excluded. Request byte counts mean bodies consumed by ASGI; a rejected route need not consume its submitted body. A favicon404 is incidental; the captured browser warning/error list is empty. No complete authenticated browser/network trace or signature verification is claimed.

## Data and gate correspondence

Both before/after SQLite checkpoints pass integrity checks. All12 tables are compared. All162 original fact rows and both retained receipt rows remain exactly unchanged. Only three new fact rows, the164→101 predecessor link, and expected fact counter advance162→165 are added. Other tables remain equal.

Five retained state responses yield786 fact/digest/scope/ingestion comparisons against actual stored rows; all five assembly digests recompute. One history response retains both pressure revisions. Three distinct save responses match their exact reviewed fact, request, canonical payload, digest and stored ingestion. There was one save per new fact, not automatic retry. Note A's first save response matches its final stored bytes; no separate intermediate after-Note-A SQLite checkpoint is claimed.

The disposable gateway health reports execution_enabled=false; an execution-route probe returns404 before protected command dispatch. These are fresh **synthetic gateway** observations, not a production service inspection. No production execution configuration changed. The standard fixture bootstrap generated its two retained synthetic examples before the initial checkpoint; no new protected preparation, execution or reconciliation was dispatched by this browser/API journey.

## UI coverage and limits

Files under original/browser-journey retain the guide, flowsheet, source/preview/history, blank/new assessment, desktop/narrow comparison, expanded authored caveats, saved and restored handover, console, asset references and layout records. Screenshot names are stage labels, not claims that every complete panel is visible.

Desktop layout was tested at1280px and narrow layout at390px, with no document overflow at the measured points. The desktop screenshot is limited by the actual visible browser surface; complete DOM supplies additional text. The narrow table can require vertical scrolling.17-final-comparison.jpg shows the normal-size header/guide, while18-final-comparison-visible.jpg shows the follow-up row and note actions, with identities above the viewport. Source disclosures are not all expanded; original/new comparison complete-record disclosures remain collapsed. These captures are not all-device, touch/pointer or accessibility certification.

This is an implementation-operated journey. An uncoached new-visitor/clinician usability pass and independent Director acceptance cannot be self-certified. Save uncertainty, committed/absent/failed lookup and explicit same-revision retry have integration/client/API regression coverage; no new live delivery-fault injection or socket-loss model is claimed here.

Only handover **selections** have bounded same-browser/profile/origin recovery. Clearing storage or changing origin can lose them. Unsaved/uncertain clinical drafts and commands remain in memory and must not be reloaded; general durable recovery is deferred. A saved selection is not a signed/sent/scheduled clinical handover.

## One Director request and evidence reuse

Use EVIDENCE-MAP.json and the source mirrors to review the consolidated db56f7e→ee81661 range, with special attention to scope/gate refresh, mounted-draft guards, stale-digest withholding, exact comparison and bounded storage/recovery. The final increment is also supplied separately against8c7fedc. Preserve C1/R1/F1/F2 closure and older code/Docker/lifecycle acceptances within their exact source/scope.

Accepted two-selection evidence1225b2e and three-selection evidence86aee664 retain captured-display scope; they are not substituted for this fresh API/database exercise. Separate8c7fedc/dac9fa19 timeout evidence retains its663/17-test attribution, not the new668 totals. No fresh container acceptance is claimed for ee81661.

Return one combined verdict: code/integration acceptance, evidence sufficiency and any remaining usability/clinical-readiness boundaries. No additional isolated ABG walkthrough or repeat suite is requested solely for publication. Real-patient authentication, patient matching, access isolation, audit/backup/restore and function-specific clinical governance remain separate work.

Production execution remains disabled. Nothing merged, deployed or hosted externally. This milestone is a local synthetic workflow candidate, not clinical validation.

## Direct review access

No ZIP or Mac access is required. ORIGINAL-SHA256SUMS covers the selected original artifacts at publication time, not a capture-time commitment. SOURCE.json/SOURCE-TREE.json and source/ provide exact integration-file mirrors and reconstructable Git identities. MIRRORS.json provides bounded lossless text parts for large/binary files. Run `python3 verify_publication.py` with Python3.11+ in a downloaded evidence tree, or recompute independently; it performs data-only hashes, Git identities and read-only SQLite/API correspondence, never the supplied app, observer server or tests. Default-build binaries are omitted; their raw successful build log remains. The authoring build actually served is retained in full.
