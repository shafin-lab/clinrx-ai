# Director review: ABG and broader echo synthetic demo

## Exact source and review boundary

- Source commit: **66725cf1d51064a7d7956aa503f897cf920057ca**
- Source tree: **cb3bca6c834514022a979350143e372932a76cf0**
- Parent hosting checkpoint: `28496c46494dcafc5440b92712eab382cd3c80de`
- [Source](https://github.com/shafin-lab/clinrx-ai/tree/66725cf1d51064a7d7956aa503f897cf920057ca)
- [Incremental diff](https://github.com/shafin-lab/clinrx-ai/compare/28496c46494dcafc5440b92712eab382cd3c80de...66725cf1d51064a7d7956aa503f897cf920057ca)
- [Scope and contract notes](https://github.com/shafin-lab/clinrx-ai/blob/66725cf1d51064a7d7956aa503f897cf920057ca/docs/SYNTHETIC-DEMO-ABG-ECHO.md)

This is a new downstream increment linked through PR #23. The accepted PR head
remains `17e2064c3f1a1761876e9a42c5c7a131646d465c`; it has not been replaced by
this review. Prior acceptance does not automatically approve the new ABG contract
or display changes. Production connected execution remains disabled. No merge or
deployment is authorized or performed. Only source/evidence review references
are published. No application branch is pushed.

## What changed

The default case has 41 fabricated records in 14 of 15 supported families, with
HPI absent and optional. Optional inclusion has separate test coverage. Seven new
ABG/haemoglobin records preserve exact values, arterial specimen, collection
assertion and source-time oxygen/ventilation settings. Echo expands to twelve
records: LVOT VTI, EF, RVSP/PASP estimates, TR velocity, RV size/function, septum,
valves, pericardium, a source PH impression and TAPSE. No PH diagnosis, PAH subtype,
acid-base interpretation, new threshold or treatment recommendation is generated.

The 15-family registry is unchanged. Four additive oxygen-family concepts and an
optional typed BloodGasContext are new. When context is absent it is omitted from
serialization to preserve historical canonical payloads. Existing PaO2 admission
semantics are unchanged. Please scrutinize contract compatibility and source
semantics rather than treating this as only a cosmetic fixture change.

## Inspect the evidence directly

- [Original validation report](original/README.md), [commands/runtime versions](original/environment.json)
- [Full backend log: 4,245 passed, one existing warning](original/backend-0.log), [command/exit code](original/backend-0.json)
- [Frontend log: 447 passed](original/frontend-pinned-0.log), [typecheck](original/frontend-pinned-1.log), [default build](original/frontend-pinned-2.log), [hosted-mode local build](original/frontend-pinned-3.log)
- [Original tested file hashes](original/source-identity.json). All 14 files were checked against their committed blobs; commit creation changed no tested bytes.
- [ABG DOM](original/abg-dom.txt), [ABG screenshot](original/abg.png), [echo DOM](original/echo-dom.txt), [full echo capture](original/echo-full.png), [overview](original/overview.png)
- [Optional-HPI empty state](original/optional-hpi-dom.txt), [correction history](original/correction-history-dom.txt), [retained withholding](original/retained-dom.txt)
- [Actual API state](original/live-state.json), [released response](original/released_example.json), [withheld response](original/withheld_example.json), [API logs](runtime-api.log)
- [Consistent SQLite snapshot](synthetic.sqlite3), [all 12 readable table exports](readable-tables.json), [exact row-array preimages](raw-row-arrays.json), [47 readable source payloads](fact-payloads/)
- [Snapshot identity](snapshot-verification.json), [portable verifier](verify_evidence.py), [verification results](verification-results.json), [complete file index](INDEX.md), [SHA-256 manifest](SHA256SUMS.json)

Download individual files through GitHub Raw/API, or fetch the evidence tag as a
Git checkout. No ZIP, Mac connection or access to localhost is required. The
portable verifier uses only Python's standard library and SQLite in read-only
mode: `python3 verify_evidence.py`. It imports no application code and contacts no
API. It checks the published bytes, table exports, original row commitments, all
41 API facts and digests, repository/cutoff/ingestion correspondence, both stored
receipts and eight complete original/terminal witnesses, plus inference identity.
It writes only its deterministic verification-results.json beside the evidence.

## Evidence timing and limitations

`original/` preserves the original local captures unmodified, including their
then-accurate references to uncommitted work. Source was committed afterward as
66725cf with all tested-file hashes identical. The consistent SQLite snapshot,
readable exports and portable verifier were added at publication time. Their
recomputed row hash matches both original API-read commitments. They are not
newly captured historical before/after snapshots of the browser session.

Original live-state read context is redacted to an unusable placeholder. No
signing key, credentials, real patient data or unrelated local files are included.
Browser capture is evidence of the implementer's exercise, not independent live
observation. External HTTPS, fresh-user access, new Linux container validation and
hosted CI are not claimed for this increment. The retained descriptive inference
is still P/L/V timing only; ABG and echo are browsable source evidence.

Please return ACCEPTED for this gated synthetic-demo scope or CHANGES REQUIRED
with reproducible findings. Distinguish application defects, evidence gaps and
future clinical-policy work. Keep production execution disabled. Do not merge,
deploy, activate execution or infer clinical readiness.
