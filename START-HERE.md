# RF2-F4 handover race — focused Director review

Application **d608ce8655a024cf7c9e4d78dbeb85b50d20fdc5**; tree **2d6ba2e912f5a847825ebd3485cd0639ea67c6e8**.
Accepted parent **195f4521002253d738685bf644564d51eb1acf4e**.

1. Read [correction/validation report](original/REPORT.md), [exact two-file source manifest](original/source/FILES.json), [diff](original/source/changes.diff) and [raw identity](source-identity/IDENTITY.json). Raw application/parent commit bytes are supplied.
2. Inspect [original logs](original/logs). Old-source negative control covers the initial7 cases:5 failures/2 passes. Final source has11 race cases plus existing safeguards: **52 focused tests/four files**, **767 full frontend tests/28 files**, typecheck/default and explicit RF2 builds passed. Final runs use maxWorkers2. Initial test-double typecheck failure and intermediate48/51 focused totals remain separately attributed. Existing bundle warning remains. No exact-head hosted CI, backend rerun or container result is claimed.
3. Compare [before](original/database-before-rows.json) and [after](original/database-after-rows.json) installation exports: all12 tables byte-identical,186 fact revisions and2 receipts. [UPDATE.json](original/UPDATE.json) and [served-build.json](original/served-build.json) report local installation/direct-HTTP build correspondence. Preserved tested build bytes are included. These are row exports, not SQLite binary checkpoints or raw integrity/foreign-key logs; those checks remain implementation-reported. Backend-start metadata plus unchanged backend source does not independently authenticate the retained process's loaded code.
4. [MIRRORS.json](MIRRORS.json) supplies lossless chunks for large text/build files: concatenate UTF8 directly, or concatenate then decode base64. Original checksum manifest is preserved. PUBLICATION-SHA256SUMS.json covers actual publication files except itself. verify_evidence.py recomputes data-only integrity; it does not operate the application/browser or rerun tests. No ZIP or Mac access is required.

## Review behavior

- A delayed restoration merges only still-selected exact references, using repository/kind/id/revision, digest and ingestion correspondence plus response-cutoff lower bound. Original selected cutoff/pins are retained; no successor substitution or pin upgrade.
- Concurrent additions keep their confirmed evidence. Removed selections cannot return. A newly confirmed record takes precedence over older returned evidence. Two same-render additions do not drop either selection.
- Repository/scope change, unmount or a newer restoration invalidates old results. Same-scope refresh and callback replacement preserve valid restoration.
- Failed lookup is separately disclosed without replacing explicit saved/unsaved status or removing confirmed additions. Missing pins remain visibly unavailable. Explicit save and existing cross-tab compare-and-swap remain; no automatic storage write or retry.
- v1 copy remains explicit, preserves v1 bytes and requires explicit v2 save.32-selection bound, exact reference checks and pending-command recovery remain intact. Editor, source-review and command transport algorithms are not remounted/replaced.

The tests use controlled deferred promises and synthetic component fixtures, not live browser fault injection. Browser storage was untouched/not inspected during installation. No browser reload, screenshot, uncoached usability, broad accessibility or authenticated network trace is established. Prior screenshot/reload evidence limitations and general durable draft/command recovery remain unresolved.

All original evidence remains unchanged. The original report's no-push wording describes local creation time; this publication adds only separate immutable source/evidence review tags and a PR23 comment. PR23 application head remains unchanged. Execution remains disabled; no merge, deployment, external hosting or gate activation. Request focused F4 closure without inferring clinical readiness or full RF2-12 acceptance.
