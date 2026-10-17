# Expanded ICU Docker packaging — local validation

Completed 17 October 2026 (Asia/Kolkata). Local source **2539eb61292456706b3c358443a8fdb7a6ece144**, tree **d286b5c30bf01bcd0d2f6ab64df0a1d082a27a27**, parent 79536d42701e5153acdd94bf04844c353c25190b. Working tree clean. Nothing pushed, merged, deployed or externally hosted; production connected execution remains disabled.

## Correction

The existing comprehensive offline CLI now has an explicit `--flowsheet` option. It invokes the existing expanded bootstrap, retains the database, prints its manifest and exits. Docker selects it only in the fixture-build stage. Omitting the option preserves the existing 41-record default. Exclusive file creation rejects existing files (including empty files), valid/dangling symlinks and relative paths; no existing database is replaced. Runtime startup remains free of seeding and still uses the separate read-only gateway. Hosting documentation records the expanded option and one-worker/one-replica boundary.

Five files changed: offline CLI, Docker recipe, hosted gateway regressions, new CLI regressions and hosting documentation. No fixture facts, clinical policies, schemas, migrations, dependency pins, production configuration or frontend code changed.

## Relevant validation

- **56 focused Python tests passed**, one existing Starlette/httpx warning, 179.75 seconds. Tests cover both comprehensive and expanded gateway datasets, complete retained original facts and terminal witness digests, all-table no-write checks, denied operations, malformed reads, calibration/flowsheet history, restart and stale/fresh contexts, offline CLI success/refusal and existing fixture behavior. Raw log: focused-backend.log. Exact command/attribution: focused-backend-command.json. Python 3.11.6; local dependency check passed.
- No full backend or frontend suite rerun was needed for this packaging change. The image's frontend stage performed `npm ci` and **VITE_SYNTHETIC_HOSTED=true npm run build**, including TypeScript; raw stages/results remain in build.log. Existing bundle-size warning remains.
- **Actual Linux ARM64 image built and started locally**, Colima/VZ, using a clean Git archive of this exact source; build 40.37 seconds. Source/tree, image details and every runtime backend Python file hash correspond to the clean archive. Image ID/digest: sha256:612977c31212cec5adcf9eb6fcd6dc8946808ac3998bd434aaadd4b7e696db0a. No registry push occurred; docker.io/library in the build log is a local name.
- Real HTTP gateway returned **156 items, 14 populated of 15 supported families, optional HPI absent**, execution_enabled=false. Both retained released/withheld responses match persisted records; original facts and all eight terminal/consumed witness pairs were checked. Calibration has retained revisions 1/2; fs-D-CHANGE history matches its exact fact. UI/assets/health reads passed; forbidden routes returned 404; malformed state/history returned 422.
- All **12 tables**, 162 fact revisions and two receipts were unchanged after allowed/denied/malformed requests and restart, and equal the never-started fixture from the same image. Both SQLite snapshots passed integrity_check.
- Same-container/same-image restart preserved byte-identical receipts. Old signed history context failed with invalid_state_context; refreshed state restored calibration and flowsheet history. Single non-root worker, no host volume mounts, port bound only to 127.0.0.1:5183.
- Test container and newly started VM were stopped after checks; 5183 is closed and Docker context remains default. Original local demo on 5179 and its data were not modified.

## Recorded non-application failures

1. First build invocation stopped before compiling because the dedicated Docker client configuration did not include the installed Buildx plugin path. That attempt also used the mirror directory; the successful attempt explicitly uses source-context/, the clean Git archive. Failed command/log preserved as build-attempt-1.*. The dedicated configuration now contains only the installed plugin directory, no user registry credentials.
2. The first final-comparison helper copied a snapshot from the older stopped test container due to a stale name. This produced the expected mismatch (old 32 fact revisions versus new 162), not evidence of mutation in the new app. Its script/log/exit and misdirected old snapshot are preserved. Correcting the copy target to clinrx-expanded-2539eb6 made the full comparison pass. No application source change or duplicate test suite was involved.

## Evidence and limits

Exact commands, raw outcomes, source archive/copies, image/container inspect, HTTP request/response bytes, table exports, packaged/final SQLite snapshots, preserved failed attempts and cleanup are retained here. verify_evidence.py uses only standard-library data checks; verification-output.json is implementer recomputation, not Director acceptance. SHA256SUMS.json covers artifacts except itself, the verification output and disposable Docker client configuration.

The captured state_context bodies contain ephemeral local read-context signatures. These are not production credentials; use a deliberate publication/redaction strategy before sharing, and preserve correspondence/byte-equality limitations if redacted. No new browser UX/fresh-visitor exercise, external HTTPS/access-control check, hosted CI or clinical validation is claimed. ARM64 only; AMD64 is untested. Independent review and any hosting authorization remain separate.
