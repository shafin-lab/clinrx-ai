# M5.2: synthetic patient-state review API

The application now exposes five scoped routes under
`/api/v1/patients/{patient_id}/encounters/{encounter_id}`:

- `GET /state?review_start=...&review_end=...`: closed aware review window, existing
  M2.1 assembly at a server-captured cutoff, all ten coverage entries, exact item
  selection digests and signed state context. Scope is the synthetic patient/encounter
  header; unsupported buckets remain explicit coverage, never clinical absence.
- `POST /temporal-review-preparations`: M5.1 execution UUID, state context and exact
  A/B/M pins. Replay the complete original assembly, call M3.1, persist inference,
  capture the post-inference cutoff and sign the unchanged M4.1 request. Server owns
  actor, target, inference identity, revision and timestamps.
- `POST /temporal-reviews`: verified command delegated unchanged to M4.3. Released
  and withheld both return 200. Exact retry recovers retained content; a different
  canonical request with the same execution UUID returns 409.
- `GET /temporal-executions/{execution_id}`: scoped storage lookup, 404 for missing
  or foreign scope, 500 for visible corrupt retained content.
- `POST /temporal-executions/{execution_id}/reconcile`: verified command and path
  identity delegated to existing reconciliation; committed_match or absent. No
  automatic execution, retry, clocks, clinical reads or governance recomputation.

Preparation and execution are separate commits. An abandoned preparation can leave
an unused immutable inference. There is no preparation table, cleanup job or recovery
framework. Unacknowledged preparation returns a bounded 503 completion_unknown APIError
with an inference-preparation message and `X-ClinRx-Stage: inference_preparation`.
It has no execution-reconcile instruction; initiate a new preparation only explicitly.
Execution completion uncertainty returns the existing 503 CompletionUnknownResponse
with execution_id, next_action=reconcile and automatic_retry=false. Keep the original
command verbatim. Absence does not trigger execution; retry is a separate explicit call.

Projections use retained A/B/M/I, witnesses, decision and storage receipt only. They
preserve decimal strings, original times, consumed versus terminal references, direct
edges, cutoffs, applicability, uncertainty, limitations, assessment/decision/finalization
and ingestion times. No complete ancestry claim is made. A withheld response suppresses
inference.statement and exposes audit provenance and reasons only. Assessment time is
an additive optional DTO field (always populated by these routes); existing M5.1
transport construction remains compatible.

## Local configuration and explicit demo

No migration, seed or database connection occurs at app import or health/knowledge
requests. Database creation remains lazy; lifespan owns its Engine unless injected.
Required configuration: `CLINRX_DATABASE_PATH` (absolute local path),
`CLINRX_ENVIRONMENT=local_synthetic_demo` (or test), and
`CLINRX_ENVELOPE_SIGNING_KEY` (secure random 32-byte key encoded as 64 hex characters).
Keep the key outside source control. The existing untimed purpose-separated HMAC
state/command protocol is unchanged. Envelopes authenticate issuance, not access or
release; they are not encrypted. Key retention/rotation remains an operator concern.

Optional configuration: `CLINRX_API_HOST` (loopback only), `CLINRX_API_PORT` (8000),
`CLINRX_ALLOWED_DEV_ORIGINS` (exact comma-separated loopback origins),
`CLINRX_MAX_REVIEW_WINDOW_SECONDS` (604800), and `CLINRX_MAX_RESPONSE_BYTES` (2097152).
Requests are bounded at 262144 bytes before parsing. State arrays/issue limits remain
M5.1 bounds. Oversize views are explicitly rejected, never truncated. M2.1 still scans
encounter-wide terminal history: use controlled synthetic/demo encounters only, with
no pagination or claim of production resource isolation.

Explicitly migrate and seed a **disposable** database from the repository root:

```sh
PYTHONPATH=backend backend/venv/bin/python -m app.demo.patient_state bootstrap --database /tmp/clinrx-patient-state-demo.sqlite3
```

The command runs reviewed Alembic migrations and existing registration/append APIs.
It prints a deterministic manifest for synthetic-p1/e1 with A at 08:00Z, M at 09:00Z,
B at 10:00Z on 2026-10-08. A/B have distinct stable and sample identities. Exact reruns
are idempotent, including after correction; no existing history is reset or deleted.
Conflicting pre-existing identities fail through existing persistence contracts.

For the released demonstration explicitly set `CLINRX_CLOCK_MODE=historical_simulation`
and `CLINRX_SIMULATION_AT=2026-10-08T12:01:00+00:00`. The synthetic grant is unchanged.
Persistence ingestion still uses real time. Default clock mode is real and never
silently backdates requests. `X-ClinRx-Mode` labels the serving configuration as
historical-synthetic-simulation or synthetic-only-real-clock. It is configuration
metadata, not a newly persisted execution clock-mode assertion. Retained timestamps
always remain authoritative. This is not live clinical execution or patient-care authority.

Run the API with raw-path access logging disabled:

```sh
PYTHONPATH=backend backend/venv/bin/python -m app.api.run
```

Fetch state, explicitly select returned A/B/M reference+digest pins, prepare, then
execute the returned command. To demonstrate withholding, prepare first and then run:

```sh
PYTHONPATH=backend backend/venv/bin/python -m app.demo.patient_state correct --database /tmp/clinrx-patient-state-demo.sqlite3
```

The correction appends A revision2 through append_revision. Executing the old command
then detects supersession and retains a withheld outcome. Correction after an already
completed execution never changes its lookup/reconciliation response.

## Privacy and compatibility

Every clinical operation checks configured synthetic scope independently of envelopes.
There is no production authentication/RBAC. Routes have no ORM or clinical predicates.
No-store also covers malformed JSON and oversized-body errors before route dependencies.
Application logs contain only correlation UUID, route template, validated execution UUID,
category/status and duration. Errors never echo submitted values, SQL or envelopes.
The launcher disables raw-path Uvicorn logging; other server/proxy/client logs remain
outside this middleware. CORS is not authorization. Existing root, health and knowledge
routes remain available. No HTTP seed/reset/history/provenance endpoint exists.

M1–M4, Kernel v1, persistence/schema, ClinicalInference, lineage and governance are
unchanged. M5.1 additions are bounded-view configuration, early no-store handling,
preparation-specific uncertainty wording and retained assessment time. Frontend/M5.3,
production PHI, authentication, patient discovery, generic history, new domains,
background jobs, automatic retry, key rotation and deployment remain deferred.
