# Local synthetic evidence entry and correction

This is an opt-in development workspace, separate from the accepted read-only Docker demo. It is not a clinician-ready entry form, production authentication, clinical validation, or permission to use patient data. Production connected execution remains disabled. No schema, policy or clinical thresholds change.

## Start locally

From the repository, with the pinned Python/Node environment available:

```sh
PYTHONPATH=backend backend/venv/bin/python tools/run_evidence_entry.py --port 5185
```

The launcher creates a fresh directory and expanded 156-record synthetic database, builds a separate frontend, and serves it on IPv4 loopback only. An optional absolute `--directory` must be empty. It never overwrites an existing workspace. The accepted Docker database/image on port 5183 are not used. Startup never seeds or resets an existing database. Stop with Ctrl+C; the disposable database remains available for inspection.

## Workflow

- Filter the source list by family or source ID. Select an exact record to correct or withdraw, and inspect its original content and bounded revision history.
- A numeric-result correction offers a raw-value field. Other fields and source context remain available in the complete structured record. A correction preserves the clinical source times unless explicitly changed; it is not a newly acquired measurement. Supersession keeps the same kind/ID and pins the selected predecessor digest. A reason and local actor attribution are required in the UI. Original nested source provenance remains visible; new top-level provenance marks the local synthetic correction and incomplete lineage. This actor name is an assertion, not authenticated clinician identity.
- New source entries use a complete JSON record under the existing contracts for all 15 evidence families. Supply full patient/encounter binding, a new stable ID/revision, timing, units, acquisition/sample context and provenance. The source provenance actor must match the entered actor name. There is no automatic copying of a selected record into a new measurement. HPI is optional. Friendly new-measurement forms remain future work.
- Validate, inspect the complete normalized record, then explicitly confirm append. Validation does not write. Decimal strings, clock uncertainty, quality, raw units and support associations retain the existing model rules. No unit conversion, inference or treatment recommendation is added.
- The repository compares the exact predecessor within the same write transaction, rejects stale corrections and conflicting exact revisions, and appends immutably. An exact canonical retry returns its original ingestion metadata even after a later successor. Old facts and clinical receipts remain unchanged.
- After a lost, malformed or unconfirmed save response, the pending draft and proposed revision remain locked in memory. Exact lookup is read-only. A committed match confirms the stored canonical content, digest, scope, repository and revision. An absent lookup does not prove rollback or trigger a write: explicit retry reuses the same submitted draft/revision. No automatic replacement or retry occurs. Reload/closure can lose this in-memory draft; durable browser recovery is not implemented.

## Isolation

Only the separate `app.demo.authoring:from_environment` factory installs these routes. Neither the normal API nor the accepted read-only gateway exposes them. The loopback gateway fixes patient/encounter scope, rejects foreign Host/Origin, remote peers and cross-site POSTs, bounds bodies with the existing middleware, and has no execution/preparation/reconciliation write routes. Its independent configuration hardcodes execution disabled and uses an ephemeral key. Local processes are inside this development trust boundary; this is not production access control.

The existing read-only summary's exact-case withholding continues to apply if its source set changes. This workspace does not generate a new patient explanation or upgrade the accepted authored explanation for edited evidence. Clinical readiness, production authorization, terminology review, friendly domain-specific entry forms and durable browser recovery remain separate work.
