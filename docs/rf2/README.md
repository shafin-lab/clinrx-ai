# Bounded local RF2 workflow

Specification a4547e215a8c4c20bd04e807d0287c5e1d575c39; baseline 5cb73212ae6104b02bad361886cd9507795d88bf. See OWNERSHIP-AND-CARRIERS.md for the completed capability/issuer/component mapping and carrier proof.

RF2 is opt-in local synthetic charting: reuse existing evidence, record genuinely new urine/fluid/weight assertions, append corrections, inspect exact history, author separate renal notes, compare their retained pins, and explicitly save/restore version 2 handover selections. Generic creatinine/body-weight observations are read-only. Existing correction owners remain in place; no observation is cloned into another fact kind.

The UI keeps source time/interval, unavailable collection metadata, clock/quality limitations and acquisition versus purpose distinct. No balance/rate/AKI calculation, diagnosis, prescription, treatment recommendation or clinical execution is added. Retained examples and original hemodynamic routes/contracts remain unchanged.

## Local build and runtime

Use the existing pinned dependencies. Build frontend with VITE_SYNTHETIC_HOSTED=true VITE_SYNTHETIC_AUTHORING=true VITE_SYNTHETIC_RF1=true VITE_SYNTHETIC_RF2=true. The RF2 flag is off by default.

Run app.demo.renal_fluid_entry_gateway:from_environment with one worker bound to 127.0.0.1. Provide CLINRX_RF2_DATABASE as an existing absolute disposable synthetic database copy, CLINRX_RF2_FRONTEND as the absolute built frontend and CLINRX_RF2_ORIGIN as the exact loopback origin. Startup never seeds/resets. Do not point this at a real-patient database. The gateway permits only fixed-scope synthetic operations; new clinical execution remains unavailable. Existing production and Docker entry points are unchanged.

## Protocol and limits

- Source-record replay uses scoped issuer/record/component identity and exact validated chart material independently of generated local IDs. Context/series namespaces are excluded. Same-key changed content requires correction; ambiguous/multiple matches or exhausted budgets cannot insert. Replaying an original after correction returns it with supersession disclosed, not resurrection.
- In the opt-in RF2 gateway, advanced legacy entry cannot create or amend an RF2-owned record. Exact already-retained requests and read-only lookup remain available first, preserving original recovery and the legacy request-size limit. Other legacy source records retain their original owner.
- Request retry/lookup instead retains the exact pending draft. Validation is separate from save. After uncertainty, lookup first; absence is not rollback proof and only an explicit identical retry is offered. General durable pending-command recovery after closure remains deferred.
- Existing metadata carriers hold one bounded RF2 entry and up to twelve separately encoded note pins, with matching context associations. New renal notes additionally carry up to twelve explicit source-review decisions in existing carriers (25/32 external entries maximum); see F1-F3-CORRECTIONS.md. Strict source metadata, canonical/digest and exact-history correspondence fail closed. No clinical model or database schema was changed.
- New entry accepts exact ordinary decimal strings such as 35.0000 or 0.50. Historical values/units outside this local entry profile remain inspectable; no implicit conversion or number extraction from source text is performed.
- A single repository cutoff and shared history accounting feed both RF1 and RF2 views. Facts already in the composite travel once, then are adapted for display. Existing response/history caps stay unchanged; duplicate payloads are not used to evade caps.
- Handover v1 remains byte-preserved. An explicit copy to the working v2 set does not save it automatically or overwrite v1. Version 2 stores bounded exact pins, never raw commands or signed contexts. Historical resolution retains originals, visible unavailable pins and repository scope. Source deletion, automatic successor substitution and cross-device synchronisation are excluded.

## Validation and attribution

Tests cover real API/storage admission, scoped source replay, component/issuer distinctions, zero/missing/interval cases, corrections, twelve-pin fit, aggregate exhaustion and a separate full-episode preservation case. Small API fixtures reduce repeated setup overhead while preserving assertions; a full ICU episode remains explicitly exercised. Frontend checks cover strict decoding, duplicate JSON members, complete reviewed-result correspondence, retained request identity, repository replacement, exact note references, shared loader, storage conflicts and v1 preservation.

The API/component fixture was generated through the actual API on a small synthetic database. It is not a browser capture and signed contexts are redacted. Existing hemodynamics regression assertions and test timeout thresholds are unchanged.

The explicit tools/validate_rf2_journey.py runner works against an already running isolated loopback RF2 server and disposable database. It records the seven-row write ledger, historical replay, exact request hashes and before/after SQLite checkpoints. It uses successful-response discard after the actual API returns and pre-dispatch absence; it does not claim socket-loss behavior or a browser exercise.

One combined validation report/evidence package is maintained outside the source checkout. Browser access was denied by the available browser tool policy; no alternative browser or headless workaround was used. API/component validation does not establish live browser, narrow-layout, pointer/accessibility, uncoached usability or clinical acceptance. Independent Director review remains required.

No merge, deployment, external hosting or execution activation is part of this milestone.

## Corrected selected-source review

See [F1–F3 corrections](F1-F3-CORRECTIONS.md). New note validation shows exact selected versus current terminal source status. Explicit historical retention and final revalidation are required before save. Later source changes reject the append without successor substitution. Exact already-retained results remain recoverable. The original legacy owner retains legacy corrections; RF2 cannot use an amount edit to erase availability or other unedited source context.
