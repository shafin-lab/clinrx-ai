# ClinRx synthetic container — local build and startup verification

**PASS — exact application source unchanged:** `28496c46494dcafc5440b92712eab382cd3c80de`  
Tree: `00aa087cce492bd94d4c36c1e0d4299d79fa7d89`  
Local image ID: `sha256:4345bbac82a23b75451cb77d2ae1a4c0fda800912b2905985dba0e05c66733f2`  
Tested platform: **Linux ARM64** on this Apple Silicon Mac through Colima/VZ.

This supplement closes the previously unexecuted **local ARM64 container build,
startup and same-container restart checks**. It does not establish external HTTPS,
access protection, external visitor acceptance, AMD64 compatibility, a hosted
service, clinical validation or permission to deploy.

## Exact build and environment

The context was exported directly from Git commit `28496c4`, with no untracked
files, local environment files or signing keys. `source-identity.json` records all
295 tracked context-file SHA-256 values. The unchanged source and Docker recipe
are accessible at https://github.com/shafin-lab/clinrx-ai/tree/28496c46494dcafc5440b92712eab382cd3c80de .

`build.json` gives the exact build command, source label, platform, duration and
exit code. `build.log` is the complete first-build log. It records the pinned
Node 22.13.0 frontend build/typecheck, Python 3.11.6 dependency installation,
offline fixture construction and final image export. `image-inspect.json` and
`docker-version.json` identify the resulting image and actual Docker engine.
No image was pushed to a registry. The tag beginning `docker.io/library` in the
local build log is a local image name, not a registry push.

The test runtime was installed through Homebrew: `installed-tool-versions.txt`
records Colima, Lima, Docker CLI and Buildx. The dedicated profile used 2 CPUs,
4 GiB RAM, a 20 GiB data disk, no host directory mounts, no SSH-agent forwarding,
no SSH-config modification and no active Docker-context switch. No login service
was installed. Container access used a dedicated, credential-free Docker client
configuration. No production environment or database was loaded.

## Executed checks

| Check | Result |
| --- | --- |
| Image build from reviewed Dockerfile | Passed, first build, exit 0 |
| Runtime startup | Passed; Python 3.11.6; dependencies consistent |
| Runtime identity | Non-root UID/GID 10001:10001; no host mounts |
| Resource/security limits | 1 CPU, 512 MiB, PID limit 128, capabilities dropped, no-new-privileges |
| Exposure | Host listener 127.0.0.1:5182 only; no LAN/public listener |
| Real state API | 26 records, all 15 families, execution_enabled=false |
| Bounded source history | CAL/1 and CAL/2 retained |
| Retained results | c901 released and c902 withheld; original support preserved |
| New/legacy execution paths | Preparation, execution, reconciliation and legacy writes return 404 |
| Other scopes/docs/database files | Unavailable, 404 |
| Malformed history request | Structured rejection, 422 |
| Browser | Real container-served CO/echo, all-family library, history, both retained outcomes |
| Mobile/keyboard | 390×844; no horizontal overflow; inspector visible/focused; focus returned on close |
| Console | No warnings/errors during captured browser exercise |
| Restart | Retained receipt response bodies byte-identical; old state context rejected; fresh state/history work |
| Original/final database comparison | All rows in all 12 tables identical |
| Packaged never-started fixture comparison | All 12 tables identical to started, exercised and restarted container |
| SQLite integrity | Both exported fixture databases report ok; migration m7_0008 |
| Shutdown | Container exits 0; VM stopped; test port closed |
| Application repository | No edits; clean at the same checkpoint; main unchanged |

The fixture comparison uses a second container created from the built image but
**never started**. Its packaged database was copied out and that disposable
reference container removed. The final database was backed up using SQLite's
backup API before export. This independently checks that application startup,
reads and restart did not add or replace stored facts/receipts. It is not a
repeat of the prior full backend/frontend suites; source has not changed.

## Evidence map

- `build.*`, `run.*`, `probes.*`, `final-checks.*`: exact commands, timing, exit codes and raw logs.
- `http-events.json`, `*-request.json`, `*-response.bin`: exact direct HTTP metadata and bytes.
- `rows-before.json`, `rows-after-probes.json`, `rows-after-restart.json`, `*-rows.json`: complete relevant database exports (all 12 tables).
- `packaged-fixture.sqlite3`, `final-fixture.sqlite3`: never-started image fixture and final container snapshot.
- `browser/`: captured desktop/mobile screenshots, DOM, focus/layout metadata, retained results and console log.
- `container-inspect.json`, `stopped-container.json`, `image-inspect.json`: runtime configuration, identity and clean exit.
- `host-port-listeners.txt`, `cleanup-check.json`: loopback-only listener and cleanup confirmation.
- `clinrx-container-*.py`: capture/check helpers; they contain Mac-local paths and execute Docker/HTTP operations when run.
- `verify_evidence.py`: portable data-only verifier. It does not run Docker, probes or the application.

Signing keys stayed in process memory. No VM SSH keys, registry credentials,
Docker authentication files or production data are part of this evidence.
The stopped test profile/image remain available for reuse; tools remain installed.
The user's original local demo was not stopped or reconfigured.

## Remaining boundary

Director still reviews the hosting increment and this evidence. Protected external
HTTPS access, fresh-visitor permissions, intended provider/project, cost/duration,
and final live hosted acceptance remain pending. Linux AMD64 and other target
platforms were not tested. A later deployment requires separate user authorization.
Production execution remains disabled. No merge, deployment or gate activation
occurred. The earlier evidence remains immutable; its Docker-unavailable statement
was accurate at the time and is superseded only for the local ARM64 checks above.
