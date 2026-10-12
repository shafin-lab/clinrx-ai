# M5.3 synthetic clinician review

React, TypeScript and Vite; one screen using the five existing M5.2 routes. No clinical predicates, trend calculations, governance decisions, new endpoints or backend changes. Exact decimal and timestamp transport strings are rendered without numeric/date conversion. References and selection digests come directly from the loaded view.

## Run locally

From the repository root, bootstrap a disposable database:

```sh
PYTHONPATH=backend backend/venv/bin/python -m app.demo.patient_state bootstrap --database /tmp/clinrx-m53-demo.sqlite3
```

In the API terminal:

```sh
export CLINRX_DATABASE_PATH=/tmp/clinrx-m53-demo.sqlite3
export CLINRX_ENVIRONMENT=local_synthetic_demo
export CLINRX_ENVELOPE_SIGNING_KEY="$(backend/venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
export CLINRX_CLOCK_MODE=historical_simulation
export CLINRX_SIMULATION_AT=2026-10-08T12:01:00+00:00
export CLINRX_ALLOWED_DEV_ORIGINS=http://127.0.0.1:5173
export CLINRX_API_PORT=8013
PYTHONPATH=backend backend/venv/bin/python -m app.api.run
```

Keep the signing key private and stable for commands issued by that server. No key belongs in Vite configuration. In a second terminal:

```sh
npm --prefix frontend ci
VITE_API_BASE_URL=http://127.0.0.1:8013 npm --prefix frontend run dev
```

Open http://127.0.0.1:5173. Defaults are copied from the checked-in demo manifest: synthetic-p1 / synthetic-e1, 2026-10-08 08:00–10:00 UTC. Optional public Vite variables: VITE_PATIENT_ID, VITE_ENCOUNTER_ID, VITE_REVIEW_START, VITE_REVIEW_END, VITE_API_BASE_URL (defaults to port 8000). Only loopback API origins are accepted. Backend CORS remains an exact origin allowlist.

Load state, choose A/B/M, Prepare, then Run. To demonstrate withholding, prepare a new review before applying the correction:

```sh
PYTHONPATH=backend backend/venv/bin/python -m app.demo.patient_state correct --database /tmp/clinrx-m53-demo.sqlite3
```

Then Run that prepared command. The retained A1 is distinct from terminal A2. An already completed review remains unchanged.

## Commands and recovery

Opaque server commands are held only in React memory; never decoded, reconstructed, logged or stored. Preparation and execution are separate. Preparation uncertainty permits explicit abandonment, not execution reconciliation. Execution uncertainty blocks a new execution and offers explicit reconciliation. committed_match displays retained content; absent permits an explicit same-command run. There is no polling or automatic POST retry.

Reload clears evidence, selections, command and session execution IDs. In particular, reloading during completion uncertainty loses this demo UI's recovery handle; reconcile before reloading. Persistent recovery, production authentication, PHI, patient search, global history, new domains and deployment remain deferred.

Provenance uses only retained execution data. Withheld statements are suppressed in both result and dialog. Unsupported coverage is Not mapped, never clinical absence. Session reviews are not complete encounter history.

## Validation

```sh
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Vitest/Testing Library cover selection pins, command reuse, preparation uncertainty, execution uncertainty, explicit committed_match/absent reconciliation, safe errors, privacy and dialog focus. No lint/format script is configured.

Browser acceptance used a disposable real SQLite database, FastAPI on 8013 and Vite on 5173. Verified loading, ten coverage entries, exact A/B/M, preparation, release, provenance, keyboard Escape/focus return, lookup, exact-command retry, missing lookup, and correction-driven withholding with consumed A1 / terminal A2. Completion-unknown/reconciliation outcomes are component/API tests rather than induced browser commit failures. Foreign-scope privacy is checked by backend compatibility tests. No production deployment or cross-browser accessibility certification is claimed.
