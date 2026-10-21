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
- [x] Run full frontend suite (981 passed), typecheck and combined preview build. The full
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
  watermark 171 after reload. Narrow layout and simulated lost-response recovery were
  covered by regression tests, not repeated in this final browser pass.
- [x] Review final diff, run `git diff --check`, and commit source, tests and this handoff
  on the local consolidation branch. No PR or deployment was created.

## Handoff

- Starting source: `d42ce159e9ce97bf887e4c97bef58df492fed0dd` on
  `codex/clinrx-consolidated-20261022`. A full local baseline copy is preserved under
  `outputs/clinrx-consolidation-20261022/baseline/` and identifies that same commit.
- Combined preview: `http://127.0.0.1:5238/?workspace=overview` (the preview is loopback
  only and remains running). It uses the explicit synthetic antibiotic gateway, serves the
  candidate build, and reads/writes only the disposable combined-preview database.
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
- Launch the already running preview by opening the URL above. For a fresh process, use the
  explicit gateway command documented in `docs/SYNTHETIC-DEMO-HOSTING.md` as a reference,
  substituting `app.demo.antibiotic_gateway:from_environment`, the absolute working-copy
  database/frontend paths, and `CLINRX_ABX_ORIGIN=http://127.0.0.1:5238`.

Historical logs remain historical. New verification belongs to the consolidation output
directory. No source is deleted or replaced from an older snapshot.

The baseline copy and working synthetic database are local review artifacts; neither
belongs to synced project sources. The baseline source archive is intentionally not added
to the implementation commit because its original Git commit is preserved above.
