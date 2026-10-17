# ClinRx Director — expanded ICU Docker packaging review

This package is directly accessible through PR #23 without a ZIP or Mac access. It contains exact source, raw local validation, readable exports and lossless text mirrors. Production connected execution remains disabled. No merge, registry push, deployment or external hosting occurred or is authorized.

## Exact identities and increment

- Source: [2539eb61292456706b3c358443a8fdb7a6ece144](https://github.com/shafin-lab/clinrx-ai/tree/2539eb61292456706b3c358443a8fdb7a6ece144).
- Tree: `d286b5c30bf01bcd0d2f6ab64df0a1d082a27a27`.
- Parent: accepted echo-wording source `79536d42701e5153acdd94bf04844c353c25190b`.
- [Exact five-file diff](https://github.com/shafin-lab/clinrx-ai/compare/79536d42701e5153acdd94bf04844c353c25190b...2539eb61292456706b3c358443a8fdb7a6ece144), [complete patch](original/source.patch), [raw commit](original/source-commit.txt), [source identity](original/source-identity.json), [tested source hashes](original/tested-source.sha256), [clean source copies](original/source-context).
- PR #23 remains draft/open at unchanged application head `17e2064c3f1a1761876e9a42c5c7a131646d465c`. Separate review tags do not update the application branch or attribute its older CI to this source.

The comprehensive offline builder now accepts an explicit `--flowsheet` option. It selects the existing ICU bootstrap, retains the database, prints its manifest and exits. Exclusive path reservation refuses existing files, empty files, valid/dangling symlinks and relative paths. Omitting the option preserves the comprehensive 41-record default. Docker selects the option only in its fixture-build stage; runtime startup remains free of seeding. The existing one-worker gateway and production execution configuration are unchanged. Hosting docs record one worker AND one replica. No fixture facts, clinical policies, schemas, migrations, dependencies or frontend code changed.

## Focused regression results

[Raw Python log](original/focused-backend.log): **56 passed**, one existing Starlette/httpx warning, 179.75 seconds. [Exact command, versions/attribution and exit](original/focused-backend-command.json). Tests cover both 41- and 156-record gateway fixtures; supported 15/populated 14 families with optional HPI absent; preserved originals and terminal witnesses; calibration and flowsheet history; allowed/malformed/denied reads with all-table equality; startup/restart and stale/fresh contexts; offline CLI exit/manifest/refusal and existing fixture behavior.

The suite began on the same Python/test bytes before commit and completed after commit. No Python/test edits occurred during or after it; documentation was finished before commit. Current source and archived tested-file hashes match. No duplicate full backend or frontend suite was run for this packaging increment.

## Actual target-architecture image

- Native Linux ARM64 through Colima/VZ on this Apple Silicon Mac. [Build command/exit](original/build.json), [raw build](original/build.log). Build succeeded in 40.37 seconds from the clean Git archive, using an isolated Docker configuration without user registry credentials.
- Frontend stage performed `npm ci` and **VITE_SYNTHETIC_HOSTED=true npm run build**, including TypeScript, inside the image build. This establishes the explicit hosted-mode build for this source; it is not an additional frontend-test run. Existing bundle warning remains.
- Image ID: `sha256:612977c31212cec5adcf9eb6fcd6dc8946808ac3998bd434aaadd4b7e696db0a`. [Image inspection](original/image-inspect.json), [engine/client versions](original/docker-version.json), [runtime source hashes](original/runtime-source-sha256.json). All 98 runtime backend Python files match the clean archive; image source label/platform correspondence was checked. ARM64 only, not AMD64. No image was pushed; docker.io/library in the log is a local image name.
- [Container run](original/run.json), [inspect](original/container-inspect.json), [non-root user](original/runtime-user.txt), [dependency consistency](original/dependency-check.txt), [Python version](original/python-version.txt). One container/worker, no host mounts, port bound only to 127.0.0.1:5183.

## Real gateway, retention and restart

[Probe source](original/probe.py), [command/exit](original/probes.json), [raw log](original/probes.log), [results](original/probe-results.json), [HTTP event metadata](original/http-events.json), [fixture manifest](original/fixture-manifest.json).

Actual state returns **156 items**, 14 populated of 15 supported families, optional HPI absent, execution_enabled=false. Both retained released/withheld responses match stored records and have byte-identical responses after same-container/same-image restart. Complete original facts and all eight final witnesses (each consumed/terminal reference and digest) match persisted bytes. Calibration has revisions 1/2; flowsheet fs-D-CHANGE history matches its exact fact. Fresh calibration and flowsheet history work after restart.

UI/assets/health reads passed. Forbidden preparation/execution/reconciliation and other denied paths return 404; malformed state/history return 422. Restart rejects the original context with invalid_state_context and refreshed state permits history again. All **12 tables**, 162 fact revisions and two receipts remain unchanged after probes and restart. They also equal the never-started packaged fixture from the exact same image; both SQLite integrity checks pass. [Final comparison source](original/final-check.py), [exit](original/final-checks.json), [raw output](original/final-checks.log), [final results](original/final-results.json).

## Directly inspectable data

- [Readable state metadata](readable-state/metadata.json), [156 per-item files](readable-state/items-index.json).
- [All 12 tables: column definitions and 170 per-row exports](readable-tables/index.json); each row preserves raw array, named columns and parsed payload when present. These correspond exactly to the published SQLite snapshot and raw row exports.
- [All large original artifacts: lossless text-mirror index](text-mirrors/index.json). Each index identifies exact original byte length/SHA-256 and ordered small base64 chunks. Decode chunks in order; no archive extraction or ZIP upload is required.
- [Packaged SQLite bytes: text chunks](text-mirrors/e350d4e0127ff335/index.json), [tested final SQLite bytes: text chunks](text-mirrors/8e5791de8edb0d0b/index.json), [original state response bytes: text chunks](text-mirrors/9f88735a36cbed0e/index.json).
- All raw originals remain under original/. The existing 415-entry original manifest is preserved; publication manifest adds the mirrors and readable exports.

Raw state_context values are retained to preserve exact request/response bytes. They are synthetic-only read contexts from the stopped local process; its generated signing key is not included, never printed and lost on restart/stop. No live account/provider credentials or real patient data are included. Do not claim these signatures were independently authenticated; verify their disclosed scope/correspondence and observed stale/fresh outcomes. This is captured HTTP evidence, not a full browser/network trace.

## Preserved unsuccessful attempts

1. [First build command/exit](original/build-attempt-1.json) and [log](original/build-attempt-1.log): stopped before compiling because the dedicated Docker configuration lacked the installed build plugin path. It also targeted the mirror directory. Successful build explicitly used the clean archive and installed plugin path. This was a validation setup failure, not a reproduced application defect.
2. [First comparison script](original/final-check-attempt-1.py), [exit](original/final-checks-attempt-1.json) and [log](original/final-checks-attempt-1.log): stale container name copied the older container's 32-revision snapshot. That wrong snapshot is preserved and explicitly excluded from success claims. Correcting the copy target to the new container made all 12-table comparisons pass. No application change or duplicate suite was used to obtain that pass.

## Cleanup, verification and boundary

[Container stop](original/stop-container.json), [runtime stop](original/stop-runtime.json), [cleanup](original/cleanup.json): both stopped, test port 5183 closed, default Docker context retained. Original 5179 demo/data were not changed. [Combined result](original/combined-results.json), [original local report](original/README.md). Their no-push wording describes the original local validation; this publication adds only source/evidence review tags.

[Portable data-only verifier](verify_evidence.py), [publication checksums](SHA256SUMS.json), [verification output](verification-output.json). These are implementation-produced checks for independent recomputation; no Director acceptance is assumed. The guide, exports and mirrors do not regenerate or replace the captured databases. Previous accepted evidence remains untouched.

Please independently review the five-file source increment, offline/default/runtime boundaries, fixture contents and retained evidence, allow/deny/no-write/restart results and exact image/source/platform correspondence. Return ACCEPTED or CHANGES REQUIRED with precise scope, evidence attribution and remaining limitations.

No fresh browser/fresh-visitor UX exercise, external HTTPS/authentication/origin protection, hosted CI, clinical validation or hosting-provider acceptance is claimed. No deployment, merge, external hosting or production execution activation is authorized. Preserve prior review acceptances.
