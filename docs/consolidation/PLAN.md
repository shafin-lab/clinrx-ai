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
- [ ] Checkpoint existing source without committing generated historical evidence builds.
- [ ] Add failing regression tests for history race, refresh invalidation, antibiotic failure,
  snapshot disclosure and reload persistence/isolation/storage failures.
- [ ] Implement each repair and verify focused tests.
- [ ] Run full frontend suite with bounded workers, typecheck, both builds and relevant
  backend source-write/recovery tests; resolve failures before final acceptance.
- [ ] Run one combined synthetic API-backed preview from a fresh database copy.
- [ ] Browser-check M7/M8 save/reload, source history, navigation and narrow layout.
- [ ] Independent final review, commit final source and publish local preview instructions.

Historical logs remain historical. New verification belongs to the consolidation output
directory. No source is deleted or replaced from an older snapshot.
