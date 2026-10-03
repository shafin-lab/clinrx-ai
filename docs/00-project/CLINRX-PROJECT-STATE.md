# ClinRx AI — Project State and Recovery Checkpoint

Last inspected: 2026-10-04. Operational handoff, not an architecture standard.

## Kernel v1 baseline and current work

Canonical frozen engineering baseline: `d52efb2b0d1759e432bf902cf5e3e65472c7e7aa`.
At the start of this documentation task, branch main, HEAD, local main and cached
origin/main matched this commit and the working tree was clean. No remote fetch was
performed; cached tracking state is not live remote verification. This task updates
this checkpoint and adds three documentation/specification files, unstaged and
uncommitted. Reverify Git state on resume rather than treating this dated statement
as a permanent description.

Phase 4 is complete. The first protected synthetic clinical execution path and explicit
commit-outcome reconciliation are implemented. Kernel v1 freezes semantics/invariants,
not every class or API name. It is not clinically validated or deployment-ready.
Git history, committed artifacts and reproducible tests take precedence over old handoffs.

## Validation checkpoint

Previously validated at the Increment 5 baseline; not rerun for this documentation task:

| Suite | Passed |
|---|---:|
| Phase 4 Increment 1 contracts | 105 |
| Increment 2 execution persistence | 74 |
| Increment 3 shared transaction | 61 |
| Increment 4 protected workflow | 138 |
| Increment 5 reconciliation | 73 |
| All weight-trend | 701 |
| Persistence/migration | 170 |
| Governance/safety | 173 |
| Persistence/history/lineage | 368 |
| Full suite | 1,250 |

Counts overlap and must not be summed. Previous diff, whitespace and Python syntax
checks passed. Passing software tests is not clinical approval. Reproduce from root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python -m pytest -q -p no:cacheprovider tests
```

The local virtual environment is not portable repository state; use pinned backend
requirements when establishing a fresh environment.

## Completed milestones

Commit milestones are used where the repository does not establish a reliable sprint number.

| Milestone | Git anchor / evidence |
|---|---|
| Engineering foundation and legacy domain/knowledge specifications | `f1fa167`; subsequent ADR/CAS documentation and PRs #1–12 |
| FastAPI skeleton, JSON knowledge listing and per-object retrieval, API/service separation | PRs #13–16; `e7fe4c8` |
| Structured clinical-knowledge retrieval with filters and deterministic relevance ranking | PR #17, `37cbe79` |
| Completed ARCH v1.1 and DATA v0.3 Drafts | `2ff21b7` |
| SAFE v0.2 Draft | `df13999` |
| Sprint 6B core clinical model prototype, Slice 1 | `c95de5d`; [implementation notes](../../backend/app/models/clinical/README.md) |
| Slice 2 release and presentation governance | `9171597`; implementation notes and governance tests |
| Sprint 7A.1 — Patient Context Persistence Foundation complete | `52ceb23`; [persistence implementation notes](../../backend/app/persistence/README.md) and persistence tests |
| Sprint 7A.2a — Immutable revision chains complete and merged | `1d4402b`; revision-chain implementation and regression tests |
| Sprint 7A.2b — Historical retrieval complete and merged | `1559435`; cutoff-bounded historical retrieval and 454-test baseline |
| Sprint 7A.2c.1 — Durable lineage complete | `73a1ff9` |
| Sprint 7B.1 Phase 1 — Weight selection/comparison | `b03f07f` |
| Phase 2 — Inference and exact lineage | `beac78f` |
| Phase 3 — Historical governance composition | `79282af` |
| Phase 4 Increment 1 — Execution contracts | `2c94229` |
| Phase 4 Increment 2 — Immutable execution persistence | `835765d` |
| Phase 4 Increment 3 — Shared transaction | `55551df` |
| Phase 4 Increment 4 — Protected execution | `27be536` |
| Phase 4 Increment 5 — Explicit reconciliation | `d52efb2` |

## Implementation boundary

Reusable clinical state supports registered patients/encounters and persisted
observations, orders, administrations and inferences. Immutable revisions, cutoff
history and exact durable lineage are implemented. Other domain categories and
longitudinal persistence remain unsupported. See [persistence notes](../../backend/app/persistence/README.md).

The synthetic weight path now composes selection/comparison, inferred evidence,
lineage, protected historical replay/final recheck, safety/fidelity/runtime evidence,
governance and immutable released/withheld execution persistence. Explicit reconciliation
verifies retained request identity without clinical recomputation. Operational failures
abort; completion uncertainty is typed; delivery is not implemented. See
[execution notes](../../backend/app/execution/README.md).

Generic governance contracts consume supplied assertions; they do not authenticate
producers. Presentation contracts exist, but there is no actual delivery/presentation
adapter. The FastAPI app remains a knowledge-retrieval skeleton, not a clinical execution
API. There is no production authentication, PHI boundary, real lab integration,
terminology/conversion service or distributed transaction guarantee.

## Freeze and next capability

- [Kernel v1 overview and invariant map](../01-architecture/CLINRX-KERNEL-001-Execution-Kernel-v1.md).
- [Capability-extension guide](../01-architecture/CLINRX-KERNEL-002-Capability-Extension-Guide.md).
- [Synthetic serum-creatinine specification](../02-clinical-standards/CLINRX-CAP-001-Synthetic-Serum-Creatinine-Trend.md).

Next separately authorized implementation: creatinine Phase A selection/comparison,
then Phase B inferred fact persistence and lineage using existing kernel primitives.
No creatinine code exists yet. No pre-slice production extraction is required. Later
durable execution needs a small transaction-adapter composition extension, separate
capability execution storage and explicit reconciliation; preserve the weight API.
Do not introduce generic trend/workflow/selector/recovery frameworks pre-emptively.

## Governing documents and known gaps

[ARCH-001 v1.1](../01-architecture/CLINRX-ARCH-001-Long-Term-Clinical-AI-Architecture.md),
[DATA-001 v0.3](../01-architecture/CLINRX-DATA-001-Clinical-Data-and-Knowledge-Standard.md)
and [SAFE-001 v0.2](../01-architecture/CLINRX-SAFE-001-Clinical-Safety-and-AI-Governance-Standard.md)
remain Draft. This engineering freeze does not amend their approval status.
“AI reasons. ClinRx governs”; preserve exact meaning, origin, uncertainty, evidence,
immutable identity and hard-stop semantics.

PROJECT_HISTORY describes an older architecture checkpoint; CAS architecture files
are placeholders. Legacy ADR references/taxonomy and missing CAS-CDS-001 remain open
as described in DATA section 50.1 and SAFE section 2. Older implementation snapshots
inside standards do not override current code. Broad context reconstruction, clinical
reassessment, reverse lineage, external-source persistence, production security,
real integration and clinical deployment validation remain deferred.

## Resume and change discipline

Inspect repository/branch/HEAD, cached remote alignment, status and staged diff first.
Preserve uncommitted work. Read the freeze/extension/spec documents and applicable
instructions. Validate the baseline before implementation; use the exact bounded
user-authorized scope. Do not infer authorization to stage, commit, push or implement
from this handoff. Record future milestones with verified code/tests and update this
dated checkpoint. Never include secrets or patient data; use synthetic fixtures only.
