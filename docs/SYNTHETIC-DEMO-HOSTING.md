# Comprehensive synthetic demo: hosting preparation

Status: local preparation only. Do not merge, deploy, enable automatic previews or
activate production execution. Director must review this change and the user must
separately authorize any deployment. The source baseline is
`8d3ce9cec1aa5c843cb25af385735d358fb02a44`; this hosting work is a new review scope.

## Architecture

One isolated container serves the compiled comprehensive website and a narrowly
allowlisted synthetic API at the same origin. This avoids a browser-to-localhost
connection and avoids widening the normal API's loopback/CORS configuration.
No production project, database, environment file or signing key is reused.

`VITE_SYNTHETIC_HOSTED=true` is an explicit build-time opt-in. In this mode the
client accepts only its own page origin (HTTPS externally; HTTP only on loopback
for local tests). It allows only M7 state/history/retained reads, keeps all existing
response decoders, and uses same-origin credentials for a hosting provider's
access-protection cookie. Default local transport still requires loopback and
omits credentials. This flag is not an authorization mechanism.

The dedicated `app.demo.hosting` entry point independently limits API access to:

- GET M7 patient state for synthetic-p1 / synthetic-e1.
- POST bounded evidence history, which reads data without appending facts.
- GET the two fixed retained synthetic receipt UUIDs ending c901 and c902.

It denies preparation, execution, reconciliation, legacy APIs, other scopes,
API documentation and arbitrary files. Hosted legacy navigation is hidden, and
`?workspace=legacy` displays an unavailable message. New circulatory execution is
also explicitly false in the underlying API configuration. Environment variables
cannot turn it on through this entry point. Normal application entry points,
clinical policy, execution services and production configuration are unchanged.

The only public files are the built index and assets. Responses use no-store,
nosniff, no-referrer, frame denial and a same-origin content security policy.
The health endpoint is liveness/mode information; the full state/history/receipt
checks below are required to establish demo readiness.

## Local build and exercise

Use the pinned Python 3.11.6 environment and installed frontend dependencies.
Choose fresh absolute paths; bootstrap refuses existing databases. From repo root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python \
  -m app.demo.comprehensive --flowsheet --database /absolute/new/synthetic.sqlite3
cd frontend
VITE_SYNTHETIC_HOSTED=true npm run build -- --outDir /absolute/new/hosted-dist
```

The explicit `--flowsheet` option builds the expanded 156-record ICU fixture,
with 14 populated families of 15 supported (optional HPI absent), emits its
manifest to stdout and exits. The database must be a new absolute path; existing
files, including empty files and symlinks, are refused without replacement.
Omitting the option preserves the 41-record comprehensive default.

Then, from repo root, serve only on loopback:

```sh
CLINRX_SYNTHETIC_DATABASE=/absolute/new/synthetic.sqlite3 \
CLINRX_SYNTHETIC_FRONTEND=/absolute/new/hosted-dist \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python \
  -m uvicorn app.demo.hosting:from_environment --factory \
  --host 127.0.0.1 --port 5181 --workers 1 --no-proxy-headers --no-access-log
```

The signing key is generated in process memory, not printed or bundled into
frontend assets. Use exactly one worker and one replica: each process owns its in-memory signing
key. After a restart old state contexts may require
refreshing the recorded state. Durable browser-session recovery remains deferred.

## Container preparation

The recipe is `deploy/synthetic-demo.Dockerfile`, with its adjacent Dockerfile-specific
ignore file. Build context is the repository root. Node 22.13.0 and Python 3.11.6
match the existing validation versions; dependency versions and locks are reused.

```sh
docker build -f deploy/synthetic-demo.Dockerfile -t clinrx-synthetic-demo:review .
docker run --rm -p 127.0.0.1:5181:8080 clinrx-synthetic-demo:review
```

These commands build/run locally; they do not publish an image or website. The
fixture stage explicitly selects `--flowsheet` to create the expanded database
and its two protected
retained examples before runtime. The server never seeds, resets or upgrades a
database at startup. It runs as a non-root user. The SQLite adapter uses immediate
transactions even for reads, so its dedicated fixture directory remains writable;
read-only here describes exposed operations, not a filesystem read-only mount.
No volume holding real data should be attached. A replacement container starts
from its packaged synthetic fixture; this demo promises no user-created persistence.

Container evidence must identify the exact integrated source/tree, resulting
image ID and tested platform. Older fixture/container acceptance does not prove
the expanded image contents. Check 156 returned items, optional HPI absence,
retained receipts and witnesses, calibration/flowsheet history, rejected writes,
unchanged tables and same-image restart recovery. Local container checks do not
establish hosting-provider or fresh-visitor acceptance.

## Director preparation findings

Director accepted the baseline `8d3ce9c` for preview preparation, not deployment.
This increment also addresses the two nonblocking findings: selecting evidence
focuses its source inspector (including on narrow screens), closing it returns
focus to the triggering card, and an unexpected execution-enabled response blocks
browsing and replaces the disabled badge with an unverified-configuration warning.
Loading and failed reads do not claim verified gate closure. Regression checks
and a 390×844 keyboard browser exercise cover these paths. These changes require
review as part of this new hosting increment.

Local restart verification preserves both retained receipt response bodies byte
for byte and all 12 database tables. An old signed state context is rejected after
the process key changes; refreshing obtains a new context. This is not durable
command recovery and does not replace hosted restart/access acceptance.

## Required checks before sharing

1. Director reviews this exact hosting source and its local evidence; any required
   fixes receive appropriate regression checks.
2. User separately authorizes a named hosting project and synthetic preview target.
   Configure access protection covering both the website and API. The gateway
   itself does not authenticate visitors. Keep access revocable and initially
   share with the intended friend only. Do not connect an automatic deployment
   trigger while publishing review source.
3. Build the container on the intended platform; verify startup, pinned runtime,
   HTTPS origin behavior and provider access protection, including API fetches.
4. At the actual preview URL verify 41 records / 14 present of 15 supported families (HPI optional and absent by default), CO/CI, ABG, broader echo,
   device/method evidence, unknowns, exact source details, CAL/1→CAL/2 history,
   ingestion timeline, and the released/withheld examples. Verify mobile layout.
5. Verify execution_enabled=false; blocked prepare/execute routes cannot write;
   compare all database table rows before/after the exercise and repeated reads.
   No preparation or execution control may be offered. Test legacy query access,
   malformed responses and unavailable service presentation.
6. Record source/tree and image identity, URLs, browser evidence and results.
   Only then provide the tested link and walkthrough. Stop the preview or revoke
   access when it is no longer wanted. Production execution remains disabled.

This is a fabricated evidence exploration demo, not clinical validation, a live
device integration, treatment guidance or permission to use real patient data.
No merge or production promotion is required to host a separately authorized preview.
