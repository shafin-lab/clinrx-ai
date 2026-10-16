# Validation of b7d8b80 corrections

Exact source b7d8b806bca6c23d3ab91f3120e36371e78ddc75; tree 94f4cdd6a824f1afe2c641e9e56a260df4f509b8. Source exported from Git into an isolated directory. All eight changed files match committed bytes and tested-source-sha256.json. The six newer local readability files are not present in that export.

- F1 negative control: original cc8aeca F1 renderer/guard files, new genuine-HPI regressions: one passed, one failed (HPI last), 21 unrelated cases skipped. Original files were used only in the isolated test copy, then restored to correction source and byte-checked.
- Corrected focused suite: 27 passed (case interpretation plus source unit mappings).
- Initial complete default-parallel run: 514 passed; three tests timed out at the existing 5-second threshold. One existing circulatory test and two new mapping-inspector cases timed out. The log is preserved; a general environmental root cause is not asserted.
- Unchanged complete suite with --maxWorkers=2: 517 passed across 13 files. No assertion, timeout threshold or production setting was relaxed. Exact command, exit 0 and elapsed 91.58 seconds are recorded in bounded-commands.json.
- Typecheck, default build and explicit VITE_SYNTHETIC_HOSTED=true local build: passed, exit 0. Existing bundle-size warning remains nonblocking.
- Python fixture generation used Python 3.11.6 and real typed HPI persistence/API retrieval. Frontend commands used the pinned Node 22.13.0/npm 10.9.2 runtime. No dependency change.
- Backend application/models/schemas/policy/execution gates/migrations are unchanged. No backend full-suite rerun, new hosted Actions, container validation or fresh exact-head browser exercise is claimed.
- Binary reconstruction: exact existing database checksum/size, SQLite integrity and all 12 tables match original exports. The optional earlier screenshot is also losslessly mirrored; its existing .png filename contains JPEG bytes. No database or image was regenerated or converted.

The running local demo also contains the separate unreviewed Combined overview, so its current UI is not presented as an exact-source browser capture for these review tags. PR #23 remains draft at unchanged accepted application head 17e2064. No merge, deployment or gate activation.
