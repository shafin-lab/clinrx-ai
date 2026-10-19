# Bounded RF2 implementation and validation

RF2 now connects urine/fluid/weight charting, source inspection, append-only correction, authored renal reassessment, exact-reference comparison and saved mixed-evidence handover in the shared synthetic patient workspace. It reuses existing creatinine, dosing weight and fluid facts. It adds no AKI staging, balance/rate calculation, diagnosis, prescription or clinical execution. RF2 contributes to M8/M9; it does not complete either module or establish clinical readiness.

## Prerequisites completed

Concrete source ownership, concept/category and issuer/component mapping is in `source/files/docs/rf2/OWNERSHIP-AND-CARRIERS.md`. Existing generic observations are read-only; original correction owners are retained. Acquisition, method and intended purpose are independent. No acquisition is inferred from dosing use or prose. Reuse adds exact pins, not quantity rows.

Replay identity includes repository/patient/encounter and issuer namespace/issuer/record namespace/record ID/concrete component. Series/context IDs and whole-record assertions without an approved issuer profile are rejected. Exact material source assertions are compared independently of local generated IDs. Replay after correction returns the original retained revision with supersession disclosed, never resurrection or silent successor substitution. Ambiguity and lookup-budget exhaustion forbid insertion.

Carrier proof uses unchanged clinical models: one metadata entry plus twelve pin entries (13/32 slots), twelve associations (12/32), maximum local narrative 4096 characters, per-entry UTF-8 cap 4096 bytes, request cap 65536 bytes and unchanged aggregate response cap 2097152 bytes. The conservative preflight produced 31156 serialized bytes with maximum entry 988 bytes; actual twelve-pin API admission and schema-drift checks pass. No model, storage, migration or dependency change was needed.

The opt-in RF2 gateway also prevents advanced legacy entry from minting or amending RF2-owned records. Existing exact canonical requests and lookup recover first under the unchanged legacy request cap. Other legacy records keep their original owner. No global production route was replaced.

## Final source and checks

Candidate: 44294015e5439f581c8107bb7a0f72a77f328406; tree eb1d921cba282bc8cce208f1282c0cd9e0a969e4. Exactly 22 files differ from baseline. Source snapshots, SHA-256/Git blob identities, raw commit and complete diff are in `source/`.

Local results:

| Check | Result and attribution |
| --- | --- |
| Full frontend | 739 passed / 25 files, 61.26 seconds; frontend subtree matches final source |
| Exact-candidate hosted CI | **4338 backend / 739 frontend passed**, typecheck, default and RF2-enabled builds passed; both checkout logs identify final 4429401 |
| Final backend integration | 45 passed, one existing warning, 96.43 seconds; final RF2 and existing entry/recovery tests |
| Full local backend | 4336 passed, one existing warning, 901.53 seconds; **pre-final 11ddd8a**, before two admission/ownership follow-ups; not an exact-final full rerun |
| Supplemental handover | Four passing local checks, 1.54 seconds; saved test artifact outside frozen source, not added to the 739 total |
| Typecheck/build | Default and explicit RF1/RF2 authoring builds passed; existing bundle warning retained |
| Carrier/schema/dependencies | Passed; migration remains m7_0008 |
| Source hygiene | Final source clean; whitespace checks passed; original accepted checkout unchanged |

Local Node 24.12.0/npm 11.6.2, Python 3.11.6. Hosted runtime attribution is separate. Final CI details are in `CI-RESULTS.md`.

Commands used include the existing pinned backend environment's `python -m pytest tests/test_renal_fluid_entry.py tests/test_synthetic_authoring.py tests/test_guided_authoring.py -q` (see raw log and source inventory for collected filenames), full `python -m pytest -q`, frontend `npm test -- --maxWorkers=2`, `npm run build`, and the same build with VITE_SYNTHETIC_HOSTED, VITE_SYNTHETIC_AUTHORING, VITE_SYNTHETIC_RF1 and VITE_SYNTHETIC_RF2 set true. Four saved supplemental component tests were copied temporarily into the frontend test directory, run and removed. No assertion, suite timeout or CI job timeout was relaxed. Intermediate failures, including fixture/typecheck mistakes and earlier interrupted runs, remain in `logs/`; final results do not reinterpret those as passing.

## Real HTTP/API journey and persistence

`api-journey/` records 25 timestamped events against the isolated local gateway, raw request bytes/hashes, redacted response bodies, actual SQLite checkpoints and all twelve table exports. The positive journey ran initial implementation 11ddd8a. The final concrete-component and legacy-owner corrections were separately checked on the final runtime; they do not retroactively authenticate that earlier exercise as a final-source browser run.

Exactly seven declared additions changed 175 revisions to 182: new urine, measured weight and fluid assertions; original renal note; urine and weight corrections; and a new renal note. All original fact rows and both retained receipts are unchanged. Only the two expected revision links and sequence counter also change. Existing creatinine and fs-WEIGHT were reused without additional quantity rows. Earlier notes retain original pins, later notes exact corrections.

Pre-dispatch absence was looked up before explicit identical submission. In the committed-response case, the client discarded a successful API result after the actual application returned; exact lookup recovered it without another save. This is application delivery-discard evidence, not socket loss. Absence is not proof of rollback. Clinical preparation and new execution endpoints were rejected.

The final `ownership-revalidation/` captures final-source rejection of ambiguous whole-record identity and the legacy-owner bypass, plus successful original-request lookup/retry. All twelve tables remain equal to the journey's after-checkpoint: 182 revisions, two receipts. Final API metadata reports execution disabled. Exact served HTML/JS/CSS bytes match `tested-build/`. This establishes HTTP/source/data correspondence, not an authenticated browser network trace.

The portable verifier recomputes nested manifest hashes, SQLite integrity/foreign keys, all row exports, 708 captured fact correspondences, 17 canonical command correspondences, both new notes' exact three-pin references and unchanged retained receipts. Data checks are implementation-run checks, ready for independent recomputation.

## Handover and uncertainty

Version 1 bytes remain unchanged. Version 2 requires explicit save; explicit v1 copy does not automatically merge or save. Exact historical pins restore without successor substitution; unavailable pins remain visible. Component tests cover save/remount restoration/removal, both-present storage, corruption/size limits, cross-tab conflict and quota failure. Supplemental tests cover positive v1 copy and late restoration during repository replacement. These use jsdom and mocked transport; no live browser localStorage export or reload capture is claimed.

Pending commands retain original scope/request through uncertainty. Lookup precedes an explicit identical retry. Repository replacement cannot silently retarget a draft or saved result. Durable recovery of general drafts and pending commands across browser closure remains deferred.

## Remaining boundary

Live browser access was blocked by browser security policy. No headless, alternate browser or indirect workaround was used. RF2-12's desktop/narrow viewport, keyboard/focus/scrolling, accessibility and uncoached-user criteria remain unverified. This implementation and API/component validation must not be presented as complete live browser or independent Director acceptance.

Production clinical execution remains disabled. No merge, deployment, external hosting or clinical-readiness approval occurred. PR #23's old application head was not changed. Review tags identify candidates for exact-source CI; they are not deployments.
