# M5.1: API contracts and application dependencies

Transport boundary only. There are no state, preparation, execution, lookup or
reconciliation routes, no response projection implementation, and no clinical
inference, governance, storage writes or frontend. Existing `/`, `/knowledge`,
`/knowledge/search` and `/knowledge/{knowledge_id}` remain registered. `/health`
returns process health only. Errors, including unknown knowledge IDs, now use a
bounded APIError instead of echoing supplied identifiers in HTTPException detail.
Successful knowledge/root response semantics remain unchanged.

## Configuration and lifecycle

`app.main.create_app(config=None, ...)` supports explicit dependencies and retains
`app.main.app` for import/ASGI compatibility. Import constructs no Engine, reads no
configuration, opens no database and runs no migration. Lifespan validates settings,
creates an application-owned Engine with the existing database factory, then disposes
it on exit. An injected Engine remains caller-owned. There is no Session dependency.
Database connections remain lazy: constructing/starting the app and calling health
or knowledge does not connect, migrate, seed or create a database file.

Required environment variables at startup:
- `CLINRX_DATABASE_PATH`: absolute local file path; existing schema is managed by
  the existing separate migration command, never by this application.
- `CLINRX_ENVIRONMENT`: `local_synthetic_demo` or `test`; no production fallback.
- `CLINRX_ENVELOPE_SIGNING_KEY`: a securely generated 32-byte random key encoded as
  64 hexadecimal characters. No built-in key. Keep it outside source control.

Optional: `CLINRX_API_HOST` (loopback only), `CLINRX_API_PORT` (8000),
`CLINRX_ALLOWED_DEV_ORIGINS` (comma-separated exact loopback origins; default none),
`CLINRX_CLOCK_MODE` (`real` by default), and `CLINRX_SIMULATION_AT` (aware time,
required only for explicitly selected `historical_simulation`). The simulation
clock returns that fixed scenario instant. It never changes persistence clocks,
grant windows or request content. Nothing executes clinically in M5.1.

Use `PYTHONPATH=backend backend/venv/bin/python -m app.api.run` for local serving.
This launcher disables Uvicorn's raw-path access log. Direct Uvicorn invocation
must also use `--no-access-log`; third-party server/proxy/client logging is outside
application middleware. Host/port settings are applied by the local launcher.
The existing ASGI import path remains usable with explicit server options.

Dependencies expose Engine, configuration, frozen synthetic scope allowlist,
server-owned actor/OutputTarget, workflow clock and both envelope codecs. Tests may
override providers or factory dependencies. No incoming actor header is trusted.
Access scopes default to synthetic-p1/synthetic-e1 and can be explicitly configured
in APIConfig. This is not authentication/RBAC. OutputTarget.request_id stays the
existing fixed synthetic request identity, never an HTTP correlation ID.

## Immutable envelope protocol v1

`StateContextCodec` binds the existing PatientStateScope, assembly profile/version,
transport version and whole-item selection-digest version. `ExecutionCommandCodec`
binds the complete existing PatientStateTemporalExecutionRequest. Both validate
models and use existing `canonical_payload`; no second clinical canonicalizer or
request matcher exists. Domain canonicality retains offsets and exact representations.

ItsDangerous 2.2.0 Signer authenticates bytes with HMAC-SHA256 and HMAC key derivation.
Purpose-specific versioned salts and signed prefixes separate state-context from
execution-command. Payload bytes are uncompressed base64url canonical JSON; tokens
are at most 65,536 ASCII bytes, bounded before verification/decoding. Canonical
payload, encoding and signature spellings are checked. No timestamp signer, expiry,
clock, unsafe deserializer or algorithm negotiation is used. Same key across process
restart preserves verification. Changing/removing that key invalidates old commands;
key rotation/recovery policy is deferred.

Envelopes are opaque to clients but not encrypted. They prove server issuance and
integrity only, not authenticated identity, access, clinical validity or release.
Send them only in request bodies; never URLs, logs or analytics. Repr hides envelope
fields, but callers must not log model dumps. Preserve a prepared command verbatim
for execute/reconcile; never regenerate its immutable timestamps/cutoffs on retry.
No issuance HTTP endpoint exists yet.

## DTOs and errors

Frozen, extra-forbidden transport contracts prepare state, explicit A/B/M pins,
prepared commands, execution, provenance, reconciliation and uncertainty responses.
Clinical decimals are strict lexical strings, not floats. Aware timestamp input
requires explicit ISO timestamps, rejects numeric epoch strings and unsupported sub-microsecond precision; existing canonical serialization rejects lossy
representations. Tuple nesting follows existing deep-immutability conventions.
Window comparison uses exact UTC instants, including DST and microseconds.

State views retain lab/medication arrays, ten coverage entries and mapping issues;
unsupported domains have coverage rather than fabricated populated buckets.
Execution response separates minimal context, governance and exact provenance.
Released and withheld are successful completed outcomes; DTOs do not evaluate them.
Provenance fixes the A/B/M roles, exact consumed/terminal references, direct edges,
original/inference/final cutoffs, applicability, uncertainty and limitations. No
populator, complete ancestry, unrelated state or clinical eligibility rule is added.
M5.2 must honor withheld presentation and map only validated backend results.

Error handlers use static messages and allowlisted validation field paths/codes;
raw errors, submitted values, SQL, bodies and stack traces are never returned.
TransactionCompletionUnknown is mapped ahead of its TransactionAborted parent to
503. When trusted request state supplies an execution UUID it returns the explicit
CompletionUnknownResponse with reconcile action and automatic_retry=false. Without
that trusted identity it returns a bounded completion_unknown APIError and invents
no execution ID. Future routes must set the ID only after validated command decoding.
Reconciliation is not implemented or triggered by an error handler.

Middleware generates a server UUID correlation ID (incoming values are ignored),
bounds request bodies at 262,144 bytes before parsing, and logs only correlation ID,
route template, typed execution UUID if supplied, status/error category and duration.
Unmatched paths log a constant. CORS allows exact configured origins, no credentials;
it is not access control. The no_store dependency opts future clinical routes into
Cache-Control: no-store; health/knowledge do not acquire that cache policy.

## Verification and deferrals

`tests/test_api_contracts.py` uses test-only routes and synthetic pure requests,
including separate-process envelope recovery, tampering, privacy, dependency
injection and app lifespan checks. No M3.1/M4.3 invocation or fact write is needed.
HTTPX 0.28.1 is a pinned development test dependency; installed Starlette currently
emits a deprecation notice recommending httpx2. This does not affect runtime APIs.

M5.2 owns all clinical product routes, original inference preparation and its
separate commit/uncertainty boundary, real response projections and demo bootstrap.
UI/frontend, production identity/PHI, new domains, auth/RBAC and schema changes are
deferred. Existing M1-M4, Kernel, governance and persistence semantics are unchanged.
