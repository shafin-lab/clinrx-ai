# M7-C — comprehensive recorded evidence and protected P/L/V product surface

## Scope and review gate

This increment exposes all 15 M7-B evidence families through scoped HTTP APIs, runtime-validated transport and clinician-facing source inspection. It is not a lactate/vasopressor or sepsis screen. Cardiac performance, Edwards/PiCCO device context, PAC/RHC, echo/POCUS, ECG/rhythm, pressure, oxygen transport, perfusion, vasoactive events, dynamic episodes, volume, source device predictions, events and signal manifests remain distinct recorded evidence. Contextual, uncertain, unsuitable and unplaced evidence remains visible. No calculator, diagnosis, treatment advice, causal interpretation, autonomous action or device integration is added. VA-ECMO, Impella and IABP remain deferred.

`APIConfig.circulatory_execution_enabled` defaults to false. Environment loading does not enable it. New preparation/execution is blocked until independent SyntheticPLVEligibility/1 enforcement review and connected end-to-end acceptance. Isolated automated integration tests explicitly enable it in test-owned configurations. This is a release gate, not authentication. Retained lookup/reconciliation and exact retry of an already committed command remain available when the gate is closed. Never change the gate merely to bypass an unsuitable evidence result.

## Public operations

Under `/api/v1/patients/{patient_id}/encounters/{encounter_id}`:

- GET `/patient-state-v3`: cutoff-bounded full recorded evidence and signed assembly context.
- POST `/circulatory-evidence-history`: signed-context, exact stable identity history at that cutoff, including corrections and their original payloads/ingestion metadata.
- POST `/circulatory-review-preparations`: explicit P/L/V pins and every independently revisioned consumed support pin, new-policy inference persistence, immutable command.
- POST `/circulatory-reviews`: protected backend execution or exact retained retry.
- GET `/circulatory-reviews/{execution_id}`: scoped retained-only receipt.
- POST `/circulatory-review-reconciliations`: explicit same-command retained-only reconciliation.

CirculatoryProductService owns composition. Route handlers do not execute SQL, use repository methods, access persistence directly or implement clinical rules. Existing synthetic access context, bounds, loopback/no-store/error/timeout infrastructure remain in force. New M7 state and command HMAC purposes and `m7-c/1` DTO transport versions cannot be confused with M5/M6 envelopes. Exact scope, selected digests, repository prefix and execution/inference identities remain bound.

## Transport and provenance

M7 DTOs reuse the full typed recorded evidence and immutable retained execution record; no source/provenance is summarized away. Receipt responses retain original selected facts/items, exact support, inference, original/inference/final cutoffs, terminal witnesses/facts, runtime/ingestion metadata and full governance decision. A released statement is displayed only for a released decision; a withheld receipt retains original evidence and inferred statement as history without presenting it as released.

The runtime schema registry is generated from backend serialization schemas by `PYTHONPATH=backend backend/venv/bin/python tools/export_circulatory_transport.py`; a backend drift test verifies the checked-in artifact. M7 reuses the existing validation engine with an isolated registry; M5/M6 default registries are unchanged. Runtime correspondence checks validate scope, identity, exact pins/edges, original/terminal references, metadata correspondence and released rendering. No clinical eligibility/governance is computed in the browser. Decimal strings, timestamp offsets, original source lexemes and exact revisions are retained without numeric/date normalization.

## Browser and recovery

All families have independent evidence cards, with complete source facts, timing, quality, device/episode context and metadata behind labelled disclosures. Correction history is fetched explicitly at the signed cutoff. Large validated provenance is rendered when opened. Selection is explicit, including support; appearing in the browser does not establish inference eligibility.

One in-flight action gate and a component generation guard reject duplicate/late responses. A failed, timed-out, malformed or post-commit projection-failed execution enters completion_unknown and preserves the original command/UUID in memory. Reconciliation is explicit; malformed/network-failed reconciliation preserves uncertainty. Absence never causes automatic retry or proves rollback. Only an explicit same-command retry is offered after absence. Before-unload warning applies to unresolved execution/preparation. Windows and selections are locked while a command is retained. No persistent browser command store, polling or automatic re-preparation/re-execution exists. Browser reload/closure can lose in-memory commands despite the warning; this limitation is deliberate and shared with the existing synthetic product.

## Synthetic bootstrap and acceptance

Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python -m app.demo.circulatory bootstrap --database /absolute/disposable.sqlite3` explicitly; application startup never seeds data. The manifest supplies patient, encounter, review window and historical simulation time. `correct` appends a reasoned pressure correction with new exact applicability evidence; it never rewrites revision 1. The dataset contains all 15 families, contextual Edwards/Swan-Ganz history, PiCCO, PAC/RHC, rhythm, uncertain quality and unplaced records. These are fabricated source assertions, not patient-care values or validation of device capability.

Acceptance requires comprehensive family browsing/source inspection and correction history with execution gated, plus isolated API/UI tests for exact release/withhold/support successors, envelope/scope/digest failures, committed/absent uncertainty, retained lookup/reconciliation, explicit retry, malformed nested transport and stale/late responses. Independent policy review and a live connected protected-lifecycle browser run are still required before opening the execution gate. Local gated browser acceptance is not a claim that connected execution has been approved.

## Compatibility

See CLINRX-M7-PLV-POLICY-001 for historical preparation disposition. Retained old receipts are decoded without invoking new eligibility. No schema/migration/dependency or generic Kernel/M5/M6/H1-D workflow change is made. The shared decoder's registry parameter defaults to its original registry; duration handling is additive for complete retained M7 governance receipts. GitHub pull requests, rather than ZIPs, are the review handoff.
