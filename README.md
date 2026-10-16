# PR #23 — directly inspectable isolated lifecycle evidence

Application source head: **17e2064c3f1a1761876e9a42c5c7a131646d465c**  
Application tree: **3723885d26a9ba62ff271361a1c8a6a7351de63c**

This evidence-only snapshot does not change the application, PR head, production gate or deployment. All scenarios use fabricated data and disposable loopback databases. **Production execution remains disabled. No merge, release, deployment or gate activation is authorized.** This is submitted implementation evidence for Director's independent review, not an acceptance verdict or clinical validation.

## Start here

- [Complete file index](INDEX.md) — every raw file and readable mirror, with direct links.
- [SHA-256 manifest](SHA256SUMS.json) — exact bytes of every published artifact except the manifest itself.
- [Original scenario report](original/README.md) and [timestamped original HTTP events](original/events.jsonl).
- [Complete correspondence verification](correspondence-verification.json), [passing output](correspondence-verification.log), and [portable stdlib verifier/exporter](export_and_verify.py).
- [Exceptional-attempt audit](EXCEPTIONAL-ATTEMPTS.md) — separate mapping of interrupted, diagnostic and accepted preparations.
- [Original gate probe](original/gate_probe.py), [recorded gate commitments](original/gate-proof.json), [actual row preimages](gate-row-preimages/) and [recomputed match](gate-row-preimages/verification.json).
- [Supplemental absent checkpoint](supplemental-absent/) — full before/after row snapshots and browser actions for the one missing checkpoint; separate from the original ten scenarios.

## E1 — raw evidence exposed

`original/` preserves all original capture bytes, including raw bodies, SQLite files, DOM text, PNG screenshots, console captures, server logs, scripts and the original checksum manifest. The old manifest verifies all 226 original files it names. `http-readable/` contains byte-identical `.json` or `.txt` mirrors so GitHub can display bodies originally named `.bin`.

`row-exports/` supplies every table from all ten original databases and the supplemental database: original payload strings, repository identity, fact revisions, ingestion sequences/timestamps, revision links and retained receipts. Individual fact and receipt JSON files include both raw stored payload and parsed content. Exact original databases remain downloadable too; no ZIP is required.

## E2 — explicit correspondence checks

The portable verifier checks all nine original retained receipts plus the supplemental receipt. Assertions cover repository IDs; request/assembly/recheck scope; original < inference <= final prefixes; original, inference and terminal ingestion bounds and row metadata; every full terminal reference and latest-at-cutoff row; all original/terminal content digests; inference witness digest/dependencies/declarations; stored receipt digests; and retained-response content equality. Gate-pending rejection retains zero receipts.

Raw execution/reconciliation request bodies are compared separately from parsed bodies and command strings. Every browser execution/reconciliation pair and the absent explicit-retry pair is byte-identical. Original gate diagnostic #68/#69 uses Python JSON whitespace, so those raw bodies differ from browser #5 while their parsed bodies and exact command strings match. No blanket byte-equality claim is made for diagnostic bodies. Gate matching retry **response** bytes remain identical to original release #5.

## E3 — checkpoints and audit

The original gate probe saved before/after hashes but did not save separate row files at those times. The retained database still contains the exact preimages of both commitments. Published `.repr.txt` preimages recompute the original Python `repr(rows)` hash exactly; their later export time is disclosed. They are not labelled as newly discovered historical snapshots.

The original absent checkpoint retains its count proof and DOM/screenshot. Because it lacked a full empty-table snapshot, only that short browser sequence was repeated on the same unchanged source in a fresh database. The supplemental harness captures every table before and after each request. [Explicit retry correspondence](supplemental-absent/explicit-retry-correspondence.json) links empty receipt rows after reconciliation, the timestamped [explicit click](supplemental-absent/browser-actions.jsonl), the byte-identical retry request, and one resulting receipt. Original and supplemental runs are not mixed.

The diagnostic preparation is mapped to its own UUID and inference row; it has no receipt. The initial interrupted attempt has no captured observable UUID and is explicitly excluded rather than silently mapped to a successful attempt. See the exceptional-attempt audit.

## Browser proof

| State | DOM | Screenshot |
| --- | --- | --- |
| Explicit primary and support selection | [selected](supplemental-absent/selected-dom.txt) | [PNG](supplemental-absent/selected.png) |
| Uncertain completion | [original malformed](original/malformed-uncertain-dom.txt) | [PNG](original/malformed-uncertain.png) |
| No receipt before explicit retry | [supplemental absence](supplemental-absent/absent-before-retry-dom.txt) | [PNG](supplemental-absent/absent-before-retry.png) |
| Explicit retry recovery | [recovered](supplemental-absent/recovered-dom.txt) | [PNG](supplemental-absent/recovered.png) |
| Closed-gate receipt recovery | [closed gate](original/gate-closed-lookup-dom.txt) | [PNG](original/final-closed-gate-recovery.png) |

## Limits and reproduction

External harness injection remains disclosed: malformed/500 delivery faults follow actual app return, timeout is 35-second delayed delivery, and absence bypasses API dispatch. Browser console captures are not a HAR. Full durable browser-session recovery is deferred; reload/closure can lose commands.

Run `python3 export_and_verify.py` from a copy of this snapshot to recompute correspondence from raw bytes. It needs only Python stdlib and no signing key, repository checkout or credentials. It rewrites derived exports with a fresh export timestamp; verify the published SHA-256 manifest before regeneration. Original capture bytes remain unchanged. Browser/harness reproduction instructions are in the original report; use a new empty output directory for any fresh run.

No signing keys, credentials, environment files or unrelated workspace files are included. Signed command envelopes are necessary captured test artifacts from stopped, disposable local services; signing keys were memory-only and were not retained. Both supplemental and original test servers are stopped. Independent review must determine whether the exposed evidence closes E1–E3.
