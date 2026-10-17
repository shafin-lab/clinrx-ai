# ClinRx AI — Project State and Recovery Checkpoint

Inspected 2026-10-15 (Asia/Calcutta). Operational checkpoint, not clinical approval.

## Verified baseline

Remote main was verified at `608888824e83e39569beaa9f1053c39cb4a943fa`, merge of
PR #18, with a clean checkout. The corrected architectural guard permits exact
application-service delegation and prohibits route-level storage operations.
H1-A is on `feature/h1-a-reproducible-ci-checkpoint`; only its four authorized
workflow/documentation files are changed, unstaged and uncommitted. Reverify live
Git state on resume; this is dated evidence.

## Implemented milestones

| Milestone | Scope and Git evidence |
|---|---|
| Kernel v1 | Immutable revisions, cutoff history, exact lineage, protected synthetic weight execution and explicit reconciliation; freeze `d52efb2` |
| Creatinine extension | Synthetic selection, inference, lineage, protected execution and reconciliation; completed through `143e6b7` |
| M1 | Typed multidomain patient-state contracts; `8d9581d` |
| M2 | Historical ownership validation and cutoff-bounded laboratory/medication assembly; `20827a8`, `8a7dde4` |
| M3 | Explicit A/B/M subset temporal inference; `6432c6d` |
| M4 | Patient-state execution contracts, immutable storage, protected execution and reconciliation; `1ee83dd`–`323b501` |
| M5 | Application dependencies, scoped synthetic review APIs and clinician demo; `9e3dc78`, `1b7b5d4`, `6217e1e` |
| M6.1 | Typed microbiology/antimicrobial contracts and durable persistence admission; `43860dc`, `010d8f2` |
| M6.2 | Bounded historical Patient State v2 assembly; `1ab0658` |
| M6.3 | Four-input microbiology/antimicrobial temporal inference; `77c712a` |
| M6.4 | Protected execution and explicit reconciliation; `a5df565` |
| M6.5 | Additive S/I/U/D review APIs, product service, demo and frontend; `bfd8989`; architectural guard correction merged at `6088888` |

Patient State v2 covers bounded recorded microbiology and antimicrobial state:
specimen/isolate/susceptibility hierarchies, contextual parents, explicit coverage
and mapping issues, exact source identities, binding witnesses and cutoffs. The
S/I/U/D workflow consumes explicit specimen, isolate, susceptibility and administration
pins. Recorded decimal/time strings and retained provenance are preserved.
Unsupported mappings and missing evidence do not establish clinical absence. This
is not general longitudinal chart reconstruction or broad clinical reasoning.

Schema head is `m6_0007`. H1-A changes no migrations, schema or dependencies.
M5 routes remain alongside additive M6.5 routes. See the
[API notes](../../backend/app/api/README.md) and
[frontend notes](../../frontend/README.md) for synthetic-only operation.

## Clinical authority and production limitations

Kernel v1 freezes engineering invariants, not clinical authority. ARCH-001 v1.1,
DATA-001 v0.3 and SAFE-001 v0.2 remain Draft. Passing software tests does not approve
these standards or authorize patient care. “AI reasons. ClinRx governs.” Preserve
exact meaning, origin, uncertainty, immutable identity and hard-stop semantics.

This is a synthetic engineering demonstration, not production-ready clinical
support. Production authentication/authorization, PHI boundaries, real lab integration,
terminology/conversion services, clinical validation and deployment qualification
remain unresolved. Synthetic access and signed envelopes are not production identity
or authorization. Preparation and execution remain separate commits; completion
uncertainty requires explicit reconciliation rather than automatic execution.

## Validation and planned work

[H1-A verification](../07-testing-validation/H1-A-VERIFICATION.md) records exact
baseline/runtime evidence, reproducible commands, current results and limitations.
Historical validation of the identical guard patch was 3,494 backend tests passed,
1 warning; current runs are recorded separately. Overlapping counts are not additive.

H1-A adds reproducible CI and this checkpoint only. GitHub-hosted execution remains
pending publication and an authorized trigger. Local validation does not establish
that GitHub Actions has run. H1-B, H1-C and H1-D remain planned and unimplemented;
their detailed scopes require separately approved specifications. M7 is proposed,
not implemented or authorized by H1-A.

## Resume discipline

Verify remote main, branch, exact HEAD, status and staged diff before continuing.
Preserve uncommitted work and use the bounded user-approved scope. This checkpoint
does not authorize staging, committing, pushing, merging, deployment or later phases.
Use synthetic fixtures only; never record secrets or patient data in evidence.
