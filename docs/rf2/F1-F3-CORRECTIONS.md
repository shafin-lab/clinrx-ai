# RF2 F1–F3 correction boundary

Parent application 44294015e5439f581c8107bb7a0f72a77f328406 and published evidence 1c776ede26347bfb791c59e958d680a7fb380226 remain unchanged. The separate local browser-fetch correction 84c648211160963c7e14308bc86ef16dbd435fbe is retained in the candidate ancestry. These changes are local synthetic workflow controls, not clinical execution or new clinical-model fields.

## F1 — outer repository isolation

History checks the outer repository against the actual repository before resolving evidence. Every pin must agree. Matching/current-repository success and foreign outer/pin failures use real API/storage tests with unchanged rows.

## F2 — correction ownership and unedited context

New cross-owner RF2 amendments are rejected. Legacy records stay on the original-owner route already used by the UI. The result is not a conversion of a legacy record into a competing renal record. The original-owner route, original availability and exact old request recovery are covered.

For RF2-owned corrections, availability is not editable in the Chart DTO and is preserved. Unchanged point/interval fields retain their complete original timestamp/clock/basis and interval context. Changed bounds do not erase the other unchanged bound. Provenance, revision links and explicit correction reason retain their existing correction semantics.

Read-only lookup and exact retained retry are checked before applying the new admission restriction. The documented pre-fix cross-owner producer remains reconstructible solely for matching retained result recovery; that path cannot append a new cross-owner amendment. Tests label the synthetic historical producer reconstruction separately from an archived producer run. Separate local verification uses copies of the two actual old note requests and captured database, retaining all twelve tables unchanged.

## F3 — explicit selected-source review and save guard

A renal note keeps its exact selected pins. First validation returns each selected reference alongside the actual current terminal reference, digest, ingestion and typed record status where available. Generic observations do not acquire fabricated withdrawal/quality fields. An unchanged source or unavailable typed status is disclosed distinctly.

The UI then requires an explicit review step. Historical or withdrawn/invalid terminal context requires an explicit per-source retention acknowledgement. It never substitutes the successor, forbids history indiscriminately or fabricates a clinical conclusion. Reviewed metadata is revalidated before the ordinary append confirmation.

For new saves, the terminal identities/digests/ingestions/statuses are checked again inside the same BEGIN IMMEDIATE transaction as the append. A later change rejects the new append. Unrelated new patient records do not invalidate the reviewed source solely by advancing the global watermark.

A command-bound `rf2_source_review_changed` rejection contains the exact request digest and disabled-execution assertion. The client only treats it as a definitive pre-append rejection when those fields validate. The original request remains displayed until explicit re-review; new acknowledgements are reset. No automatic replacement, retry or append occurs. Other unconfirmed/network/malformed failures retain the existing uncertain state, original request and exact lookup/identical-retry rules.

Existing matching saved results are returned before the new current-source guard. A later correction cannot invalidate or rewrite a retained note or change its pending command identity. An old unsaved/unreviewed request cannot create a new note under the corrected rules; lookup stays available and the request is not silently upgraded.

### Existing carrier fit

Selected pins retain `clinrx.local.rf2.pin/v1`. Review decisions use separate bounded `clinrx.local.rf2.review/v1` entries, at most one per pin, with the authored actor/time in existing fact provenance. The unchanged clinical event supports 32 external entries and 32 associations. Maximum use is one metadata + twelve pins + twelve review decisions = 25/32 entries; twelve associations remain 12/32.

The updated probe validates maximum supported source identifiers and twelve complete reviews through strict DTOs: 49,611-byte fact, 27,560-byte request and 2,672-byte largest entry. Caps remain 65,536 request bytes, 4,096 entry bytes and 2,097,152 response bytes. No implicit model/storage redesign or limit relaxation was needed. Older note metadata/bytes remain readable without adding a default review field to their request canonicalization.

## Validation attribution and exclusions

Regressions exercise correction/withdrawal between selection and validation and between validation and save, unchanged sources, explicit historical retention, later change after acknowledgement, command-bound rejection, exact pending request recovery and no successor substitution. Real disposable API fixtures additionally exercise frontend decoding of stored review decisions and the shared catalog. They are not live browser captures.

Original publication manifests/checkpoints are retained. New tests use disposable repositories/copies; the local patient's source database and browser handover storage are not modified by regression execution. Evidence/report outside this source checkout records exact counts, failures and final source/CI identity.

RF2-F4's nonblocking same-scope handover hydration race and RF2-12 live browser/usability gap are not closed by these F1–F3 changes. No merge, deployment, external hosting, execution activation, container or clinical-readiness acceptance follows. General durable browser-session command/draft recovery remains deferred.
