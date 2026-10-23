# ClinRx candidate consolidation — 22 October 2026

The user authorized preserving and consolidating the current candidate, repairing the
reviewed integration issues, persisting reviews across reload, and one working preview.
Work stays in the existing isolated candidate; production and synced sources are untouched.

## Agreed scope and implementation decisions

- Preserve the full pre-change candidate in `outputs/clinrx-consolidation-20261022/`
  and checkpoint source, documents and tests on a local consolidation branch.
- Guard antibiotic history by selected source, snapshot, request generation and unmount.
- Keep the atomic antibiotic bundle when available. On its failure, independently confirm
  the existing RF2 catalog for the other views, clearly mark antibiotic unavailability,
  and block antibiotic actions. Never merge independently fetched clinical snapshots.
- The daily chart deliberately retrieves a different window. Display its repository cutoff
  and the shared assessment cutoff, with a visible difference notice when they differ.
  Do not imply they are one snapshot or pin daily sources into an earlier review.
- Retain completed M7/M8 manual reviews in versioned browser storage scoped by domain,
  patient, encounter and repository. Preserve exact snapshots and pins, label changed
  snapshots historical, reject invalid stored bytes, and prevent concurrent overwrite.
  This is same-browser synthetic persistence, not authenticated hospital charting.
- Preserve existing review form controls and entry/correction/recovery semantics.

## Execution and verification ledger

- [x] Inspect current source, root causes, instructions, prior evidence and other chat state.
- [x] Archive existing work and record its original source hashes/status.
- [x] Checkpoint existing source without committing generated historical evidence builds.
- [x] Add failing regression tests for history race, refresh invalidation, antibiotic failure,
  snapshot disclosure and reload persistence/isolation/storage failures.
- [x] Implement each repair and verify focused tests.
- [x] Run full frontend suite (983 passed), typecheck and combined preview build. The full
  backend suite reported 4,363 passed and two schema-export import failures because the
  repository root was omitted from `PYTHONPATH`; both failures passed when rerun with the
  repository root included. Backend source was unchanged. The installed Starlette/httpx
  deprecation warning remains.
- [x] Run the combined synthetic API-backed preview against the preserved working copy at
  `review-evidence/consolidation/clinrx-m8-combined-preview.sqlite3`, cloned from the
  untouched starting copy. The API gate reports `execution_enabled=false`.
- [x] Browser-check M7/M8 save and reload, historical reviews, kidney source correction and
  overview navigation, antibiotic patient review/reference separation, and the test-only
  non-delivery entry in patient overview. M8 and M7 reviews stayed tied to repository
  watermark 171 after reload. Simulated lost-response recovery is covered by regression
  tests. A targeted Web Lock regression reproduced stale evidence callbacks in both M7 and
  M8; saves now recheck the latest rendered evidence identity when the lock is acquired.
  Both regression tests pass. Narrow-layout review at 390×844 confirmed M7/M8 forms and
  source drawers fit, antibiotic controls and entry form have no horizontal overflow, and
  the 24-hour fluid chart advances horizontally to later hours. No review, dose, or source
  entry was saved during browser verification.
- [x] Review final diff, run `git diff --check`, and commit source, tests and this handoff
  on the local consolidation branch. No PR or deployment was created.

## Handoff

- Starting source: `d42ce159e9ce97bf887e4c97bef58df492fed0dd` on
  `codex/clinrx-consolidated-20261022`. A full local baseline copy is preserved under
  `outputs/clinrx-consolidation-20261022/baseline/` and identifies that same commit.
- Candidate implementation: `29c7a317459556a452685066835cd664fcf98ac0`.
- Combined preview: `http://127.0.0.1:5238/?workspace=overview` (the preview is loopback
  only and remains running). It uses the explicit synthetic antibiotic gateway, serves the
  candidate build, and reads/writes only the disposable combined-preview database. The
  active asset directory is `review-evidence/consolidation/builds/preview-20261022T075308Z`; use
  `tools/build_connected_preview.sh` for later builds so the running asset directory is
  never replaced by a default, unconfigured frontend build.
- Working database was cloned from
  `review-evidence/consolidation/clinrx-m8-starting-copy.sqlite3`; that original file still
  has SHA-256
  `0874008ff2c62f8a4a711b0c08c33f58e1d6b37a2304a4314faca55b87083f54`.
- One clearly labelled synthetic `not_given` antibiotic record was saved to the disposable
  copy to verify overview propagation. No medication dose was recorded or administered.
- M7/M8 completed reviews survive reload in this browser using versioned local browser
  storage. They are synthetic notes, not shared hospital documentation or clinical
  sign-off. Exact repository snapshots and source digests remain pinned; changed evidence
  leaves earlier notes historical.
- Antibiotic catalogue, culture review, prescription/administration history, validation,
  save and exact lookup are exposed in the candidate workflow. The current patient fixture
  has no usable susceptibility report, so no culture-matched option is offered. Local
  clinical execution remains disabled.
- The already running preview can be reopened at the URL above. To launch a fresh process
  from the repository root, build the candidate frontend with the same flags used for
  verification and then run the explicit loopback antibiotic gateway:

  ```sh
  ./tools/build_connected_preview.sh
  cd ..
  CLINRX_ABX_DATABASE="$PWD/review-evidence/consolidation/clinrx-m8-combined-preview.sqlite3" \
  CLINRX_ABX_FRONTEND="<the versioned directory printed by the build script>" \
  CLINRX_ABX_ORIGIN=http://127.0.0.1:5238 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=backend /private/tmp/clinrx-preview-venv/bin/python \
    -m uvicorn app.demo.antibiotic_gateway:from_environment --factory \
    --host 127.0.0.1 --port 5238 --workers 1 --no-proxy-headers --no-access-log
  ```

Historical logs remain historical. New verification belongs to the consolidation output
directory. No source is deleted or replaced from an older snapshot.

## M8–M18 correction work — 22 October 2026

- [x] Reopened the combined loopback preview from its explicitly configured asset build;
  verified the overview, M7, M8 and antibiotic navigation and existing synthetic overview.
- [x] Added a unique versioned preview-build script with the required hosted-workspace
  flags. It refuses to reuse an existing output folder.
- [x] M7 now withholds source-limitation and recorded-issue counts unless the current
  evidence request is confirmed; unavailable retrieval no longer reads as zero issues.
- [x] Implement the first shared laboratory-import slice (chemistry and urinalysis), with
  typed source identity, correction lineage and availability cutoffs, then expose those
  same records in the overview and M8.
- [x] Reuse M6 microbiology ownership for cultures; connect report status to antibiotic
  patient review without turning culture evidence into a treatment recommendation.
- [x] Complete the M7 trend/event presentation with separate source-linked readings in
  descending source-time order, untimed readings last, and separate vasoactive-delivery
  and contextual-event groups in source-time order. Keep pressure components separate
  and retain source quality/method. Vasoactive event labels do not imply ongoing delivery.
- [x] Make Add information list the supported recorded-weight, fluid/urine-chart and
  laboratory-result workflows explicitly.
- [x] Run focused M7, overview and shared-workspace suites (46 passed), typecheck and a new
  versioned build. Reloaded M7 at 5238 and confirmed the time-ordered source-linked readings,
  separate chronological event groups, existing session reviews and disabled clinical
  execution. No records were saved.
- [x] Full frontend suite rerun with two workers: **999 passed across 43 files**. The prior
  one-test timeout was transient; the isolated retry and this full rerun both pass.
- [x] Add the latest saved M7 and M8 review summaries and next-review plans to the overview.
  Reuse the validated browser review store; label reviews historical if retrieval is
  unconfirmed or the exact repository snapshot differs. No reminders or chart writes.
- [x] Rebuild and reload the final M7 and overview previews. Confirmed the overview shows
  both saved reviews as current-snapshot matches and preserves the existing TEST ONLY
  `not_given` antibiotic entry. Active asset build:
- [x] Reshape the overview into a recorded course grouped by kidney/electrolyte/urine,
  culture/antibiotics, circulation/support and other findings. Each finding shows its latest
  timestamped source value; expanding it retains source values, statuses and correction
  context. Report status/conflict labels stay explicit, cultures and antibiotic records are
  nested together, and source counts stay in coverage details. No diagnosis/severity ranking
  or interpretation is generated. Focused overview/antibiotic tests pass.
- [x] Build the course overview in a versioned production bundle:
  `review-evidence/consolidation/builds/preview-20261022T075308Z`.
- [x] Rerun the complete backend suite after the prior schema compatibility fixes:
  **4,375 passed**, with one existing Starlette/httpx deprecation warning.

The baseline copy and working synthetic database are local review artifacts; neither
belongs to synced project sources. The baseline source archive is intentionally not added
to the implementation commit because its original Git commit is preserved above.

## Shared laboratory capture and Antibiotic culture review — 22 October 2026

- [x] Add typed, append-only laboratory report persistence and a bounded loopback endpoint.
  The initial entry catalog supports weight-independent chemistry and urinalysis mappings,
  including urea/BUN, sodium, potassium and urine findings; unmapped source codes remain
  explicit instead of being inferred.
- [x] Connect Add information to the same patient overview and M8 catalog with source,
  collection/report timing, exact patient scope, units, correction lineage and read-back.
  The existing synthetic database was backed up before the additive `m8_0009` migration;
  migration retained all 171 existing evidence facts.
- [x] Add Antibiotics tabs for Culture review, Prescriptions & administrations, and
  Reference library. Culture cards keep specimen and collection context with pending,
  preliminary, final no-growth, positive and corrected status. Organism isolates remain
  separate; susceptible options are grouped with each organism and other AST results stay
  available beneath them. Original report content and revision history remain inspectable.
- [x] Keep reported susceptibility separate from patient-specific options. The latter
  remains unavailable until infection site, allergies, renal function/support, current
  antibiotics and approved local guidance can all be reviewed. No antibiotic ranking or
  generated regimen is presented. A susceptibility selection opens a blank prescription
  review with the exact culture reference attached; current treatment, dose review,
  prescription save and administration remain separate steps.
- [x] Invalidate a selected culture when its exact evidence snapshot changes, prompt a new
  review, and reject stale linked references at persistence. The current synthetic patient
  has no usable culture report, so the live view clearly says no linked specimen groups are
  available.
- [x] Full frontend suite: 991 tests passed; typecheck and versioned preview build passed.
  Reloaded the live preview and checked all three Antibiotics tabs read-only. The existing
  test-only non-delivery record remained present; no new record was saved.
- [x] M7 presentation follow-up: chronological sorting, date-only/untimed handling, exact
  source navigation, distinct vasoactive event labels, and separate contextual events are
  covered. Updated preview build:
  `review-evidence/consolidation/builds/preview-20261022T075308Z`.
- [x] Overview review summaries: focused connected-overview (11) and shared-workspace (5)
  suites pass; live preview shows retained M7/M8 notes with matching current evidence
  snapshots and next plans. Existing antibiotic test record remains present. No records
  were saved during verification.
- [x] The first full backend run completed with 4,348 passing and 27 failing. All 27 were
  traced to the new fact-kind/schema revision interacting with migration assertions and
  existing M7 compatibility consumers. Updated those assertions and kept the unchanged M7
  execution readers compatible with `m7_0008`; the exact 28-test failure subset and a
  focused 43-test run covering laboratory, antibiotics, migration and M7 compatibility
  then passed.
- [x] Rerun the maintained backend suite after those compatibility fixes: **4,378 passed**
  with one existing Starlette/httpx deprecation warning. The top-level repository test
  invocation also collects archived source snapshots with duplicate test-module names, so
  the maintained suite was run explicitly from `tests/`.

The shared patient overview preview and candidate source remain synthetic and loopback-only.
The local synced `sources/` tree remains read-only; no source project documents or live
clinical records were edited.

## Display corrections and populated laboratory/culture verification — 22 October 2026

- [x] Correct type-aware overview summaries, withdrawn-record headlines and independent
  culture availability messaging. New regressions cover narrative/category/context records,
  genuinely missing numeric results, withdrawn values, non-delivery without a culture,
  pending culture, and final no-growth. Targeted frontend/backend suites pass.
- [x] Populate only the isolated verification database
  `review-evidence/consolidation/clinrx-display-verification-20261022.sqlite3` through the
  supported RF2 laboratory import and microbiology persistence owners. It contains distinct
  Urea/BUN results, specimen-flagged sodium/potassium, urinalysis qualitative/graded and
  microscopy components, blood-gas results, and pending/no-growth/positive/mixed-isolate/
  corrected susceptibility reports. Exact reimports were idempotent, corrected reports
  retained predecessors, and results unavailable by an earlier cutoff stayed excluded.
- [x] Verify overview and M8 at the same repository watermark (194), including original
  laboratory report/specimen details and revision history. Verify pending and final culture
  status, isolate-specific AST, corrected AST lineage, explicit missing-context gaps, and
  that the existing synthetic `not_given` entry remains visible. Culture selection opened a
  blank prescription review with the exact report reference; the unsubmitted draft was
  cancelled, evidence changes made the prior selection stale, and no medication or
  administration was saved.
- [x] Full validation: frontend **1,003 passed** across 43 files; maintained backend
  **4,378 passed**; typecheck, production build and `git diff --check` pass. One existing
  Starlette/httpx deprecation warning and the Vite large-chunk advisory remain.
- [x] Promote versioned assets
  `review-evidence/consolidation/builds/preview-20261022T110545Z` to the existing
  `http://127.0.0.1:5238/?workspace=overview&reviewBuild=110545` preview. The patient DB
  remains at SHA256
  `0fad90871d2a4fa1a36eac09c70c53fce553ea62c729d7c0b0f22038d661d2c4` and passes SQLite
  integrity check. Existing M7/M8 browser reviews remain present with their original
  snapshots and current evidence scope. Rollback assets remain available at
  `review-evidence/consolidation/builds/preview-20261022T075308Z`.
- [x] Inspect the promoted overview at the browser's narrowest available side-panel width;
  the navigation wraps, findings remain in a readable single-column flow where needed, and
  the fluid chart has explicit horizontal scrolling for its wide hourly table. The requested
  390×844 override was clamped by the in-app browser to a 630px CSS viewport (`innerWidth`),
  so an exact 390px browser rendering could not be confirmed in this session.
- [x] Preserve baseline manifest `review-evidence/consolidation/display-corrections-baseline-20261022.json`
  and the pre-migration SQLite backup. The populated verification database remains separate
  and uses the isolated browser origin on port 5240.

## CrCl calculator simplification — 23 October 2026

- [x] Reduce the Cockcroft–Gault calculator to exactly its equation inputs: age, equation sex
  coefficient, weight in kg, and serum creatinine in mg/dL. Remove weight-source, weight-basis,
  creatinine-source, renal-function-assessment and kidney-support controls from the calculation.
- [x] Keep renal stability and kidney-support selection in the separate antibiotic dose-review
  context, where they continue to gate non-dialysis and CRRT/intermittent-HD candidate profiles.
  The CrCl number remains an estimate and never selects a dose by itself.
- [x] Regression checks: focused antibiotic workflow/dose suites pass (39). A full frontend
  rerun in single-thread, non-isolated mode passed 997 tests and reported six failures in
  unrelated recovery/workspace/investigation tests (four timeouts and two duplicate-button
  queries); the regular isolated run also had worker-start/timeouts. The production build and
  TypeScript typecheck pass; `git diff --check` passes. The existing large-chunk Vite advisory
  remains.
- [x] Promote `review-evidence/consolidation/builds/preview-20261022T182117Z` to the existing
  `http://127.0.0.1:5238/?workspace=overview&reviewBuild=182117` preview. The live calculator
  displayed 38.2 mL/min from transient test inputs; the renal dose-review section separately
  presents renal status and kidney support. Inputs were cleared, and no medication was saved.
  Patient database hash remains `0fad90871d2a4fa1a36eac09c70c53fce553ea62c729d7c0b0f22038d661d2c4`
  (SQLite integrity check: `ok`). Rollback assets:
  `review-evidence/consolidation/builds/preview-20261022T112653Z`.
