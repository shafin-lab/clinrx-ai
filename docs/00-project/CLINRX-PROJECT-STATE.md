# ClinRx AI — Project State and Recovery Checkpoint

Last verified: 2026-09-30. Operational handoff only; this is not an architecture standard.

## Purpose and stable baseline

ClinRx AI is a clinical decision-support platform being built around structured knowledge, patient context, traceable evidence, deterministic computation and governed AI assistance. It supports clinician judgment; the current repository is a development prototype, not an approved patient-care system.

- Stable `main` baseline: `1559435b68dae3b8ffdcf34fa1da07dfd5611e66` — `add cutoff-bounded historical retrieval` (Sprint 7A.2b; 454 tests).
- Current branch: `feature/sprint-7a2c1-lineage-resolution`. HEAD, local `main` and cached `origin/main` match that baseline. No network fetch was performed; cached tracking state is not a claim of live remote synchronization.
- Sprint 7A.2c.1 implementation and focused adversarial review are complete locally but **uncommitted**. After this checkpoint update there are four modified tracked files and two untracked files; the index is empty. Nothing has been staged, committed, pushed or merged for this slice. Reverify this dated state when resuming.
- **Git history, committed repository artifacts, current code and reproducible tests are authoritative over conversational memory.** This file is a navigation aid; resolve discrepancies from those artifacts and record the result.

## Test baseline

Verified for the current uncommitted feature state: **549 passed**, including **95 focused lineage tests**, using Python 3.11.6 and pytest 9.1.1 with bytecode and pytest cache disabled. The focused adversarial review added 18 cases, found no reproducible defect and required no production-code change. This supersedes the Sprint 7A.1 checkpoint; it does not attribute the new tests to the stable baseline.

Coverage includes [retrieval tests](../../tests/test_retrieval_service.py), [clinical models](../../tests/test_clinical_models.py), [governance](../../tests/test_governance.py), [persistence](../../tests/test_persistence.py), [persistence corrections](../../tests/test_persistence_corrections.py), [revision chains](../../tests/test_revision_chains.py), [historical retrieval](../../tests/test_historical_retrieval.py) and [durable lineage](../../tests/test_persistence_lineage.py). Review checks covered exact budget boundaries, repeated endpoint work, association/evidence overlap, nested immutability, DST folds, read-only SQL and rollback without partial results, alongside the existing cutoff, provenance and privacy cases. Passing software tests is not clinical validation.

Run from the repository root, without generating bytecode or pytest cache:

```sh
PYTEST_ADDOPTS='-p no:cacheprovider' PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python -m pytest -q
git diff --check
```

The existing virtual environment is local setup, not a portable repository artifact. [Backend requirements](../../backend/requirements.txt) pin runtime dependencies; [development requirements](../../backend/requirements-dev.txt) include pinned migration and test dependencies. A fresh session must establish its test environment explicitly rather than assume the environment already exists.

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
| Sprint 7A.2c.1 — Read-only durable lineage resolution complete locally | Uncommitted on `feature/sprint-7a2c1-lineage-resolution`; 95 focused / 549 complete tests after adversarial review |

## Implemented capabilities

- [FastAPI application](../../backend/app/main.py): root status, `/knowledge`, `/knowledge/search`, and `/knowledge/{knowledge_id}`. Knowledge is loaded from two JSON objects in `knowledge/objects/`; search supports query/domain/status/object-class filtering and deterministic ranking.
- [Clinical models](../../backend/app/models/clinical/README.md): Pydantic contracts for patient/encounter context, seven fact categories, units/missingness, medication orders versus administrations, calculation execution provenance, immutable snapshots and bounded lineage checks.
- Separate candidate, rendering, safety-evaluation and human-decision records, with revision/content consistency checks and JSON round-trip coverage. Some derived properties intentionally remain Python-only; consult the implementation notes before designing APIs.
- [Governance service](../../backend/app/services/governance_service.py): pure release assessment/decision and presentation assessment/recording functions. Contracts bind exact payload, policy, context, authority, freshness, warning exceptions and final-delivery evidence; they record withheld, unconfirmed or rejected outcomes as appropriate.
- These functions consume supplied assertions. They do not authenticate producers, validate natural-language clinical meaning, inspect live patient systems, persist records or actually display content. No clinical-model/governance API is wired into the application.
- [Persistence foundation](../../backend/app/persistence/README.md): SQLAlchemy 2.x, file-backed SQLite for local/synthetic development and Alembic migrations, with independent domain and persistence models. Supports patient/encounter registration and ownership, plus ClinicalObservation, MedicationOrder, MedicationAdministration and ClinicalInference persistence with exact-reference retrieval. Repository ingestion metadata, canonical retained-representation idempotency, transactional rollback and committed close/reopen durability are implemented; broader recovery/concurrency guarantees remain deferred.

## Durable clinical history and lineage boundaries

- **7A.2a revision history:** reasoned immutable linear chains per stable fact, exact canonical retries before terminal-predecessor enforcement, atomic revision/link writes and fixed patient/encounter ownership. SQLite serializes repository units with BEGIN IMMEDIATE; this does not establish PostgreSQL or crash-recovery guarantees.
- **7A.2b historical retrieval:** repository UUID plus ingestion watermark defines visibility before revision-prefix validation. Latest-known selection precedes clinical/ingestion-time filtering, so older revisions cannot be resurrected by filtering. Sequence gaps are valid and clock time cannot replace the watermark. Instant comparisons use exact integer arithmetic, including datetime boundaries and DST folds.
- **7A.2c.1 durable lineage:** `resolve_lineage(reference, *, target, cutoff, limits)` resolves declarations already retained in immutable fact payloads within one explicit patient/encounter prefix. Exact A1 dependencies remain A1 after correction A2; neither revision links nor order associations become evidence dependencies. Confirmation bases provide evidence; confirmation targets provide validation context. Shared exact or stable-family ancestry rejects independence assertions; disjoint ancestry remains unknown. Declared inferred/derived origin is preserved rather than promoted by copying or confirmation.
- Visibility precedes lineage extraction/traversal/validation. Future facts, revisions and malformed future lineage cannot alter an earlier result. Missing supported endpoints share `not_resolvable_in_scope_at_cutoff`; unsupported kinds remain explicit. No out-of-scope/future lookup refines the missing reason. An ancestor may arrive after its dependent and resolve at a newer cutoff without changing old-cutoff replay.
- Iterative bounded traversal handles repeated ancestors, diamonds and longest evidence paths. Cycles, malformed retained state and exhausted budgets fail explicitly with sanitized errors; no partial-success result escapes structural failure. Results retain immutable facts/metadata, typed assertions, separate associations, unresolved reasons, origin/provenance limitations and resolution coverage. Complete resolution of the declared graph is not source/clinical completeness or proof of independence.
- The resolver is persistence-only and read-only: no new table, migration, lineage watermark, domain contract, canonical format or write-acceptance change. Visible scoped history is validated even when unrelated to the root; unrelated visible corruption can therefore fail a query. Row/graph budgets are not payload-byte or wall-clock limits. The resolver cannot detect undeclared copying when external lineage is unavailable.

## Governing standards and principles

Use the committed standards as the governing design references; **all remain Draft**, not clinical-use approvals.

| Standard | Version | Responsibility |
|---|---|---|
| [CLINRX-ARCH-001](../01-architecture/CLINRX-ARCH-001-Long-Term-Clinical-AI-Architecture.md) | 1.1 | System responsibilities and release boundaries |
| [CLINRX-DATA-001](../01-architecture/CLINRX-DATA-001-Clinical-Data-and-Knowledge-Standard.md) | 0.3 | Logical information, versions, provenance and disposition |
| [CLINRX-SAFE-001](../01-architecture/CLINRX-SAFE-001-Clinical-Safety-and-AI-Governance-Standard.md) | 0.2 | Safety decisions, assurance, oversight and release gates |

Preserve: “AI reasons. ClinRx governs”; exact clinical meaning validated before release; stable identities and immutable revisions; explicit origin, uncertainty and clinical time; deterministic computation; distinct evidence and knowledge; non-overrideable hard failures; auditable human decisions; technology/provider independence. Detailed requirements belong in the linked standards, not this checkpoint.

## Current clinical model and governance pipeline

Source facts and verified context → immutable snapshot → structured candidate → exact rendering/payload → safety and meaning assertions → release eligibility/decision → current presentation eligibility → final destination verification and delivery receipt → presentation record.

The code enforces structural consistency over supplied evidence, including freshness/dependency/authority windows and warning-exception bindings. Final verification and receipt represent trusted adapter attestations, not proof of physical delivery or clinician comprehension. Changed content or assertions require new revisions; acknowledgement cannot convert a failed evaluation into a pass. Retrieval remains a separate prototype, not an integrated end-to-end clinical reasoning pipeline.

## Deliberate deferrals and next phase

- PatientContext reconstruction, ContextSnapshots, historical knowledge reconstruction and a broader durable audit system remain deferred. Revision chains and cutoff-aware patient-fact history are implemented; read-only declared-lineage resolution is complete locally. Reverse dependent lookup, prospective lineage write validation, standalone links, external-source persistence, cross-encounter reconciliation, automatic reassessment, invalidation and retraction are not part of 7A.2c.1. PostgreSQL support is not validated; production PHI use and clinical validation remain unsupported.
- No live patient ingestion, authenticated assertion producers, revocation feeds, trustworthy-clock infrastructure or atomic display adapter.
- No clinical algorithms/rule engine, terminology/unit conversion service, FHIR mapping, medication reconciliation, governed evidence retrieval, external AI integration or clinical deployment validation.
- Frontend, mobile, infrastructure and CI workflow directories remain placeholders. Privacy/retention enforcement and operational recovery integrations are future work.

**Next action:** review and explicitly authorize staging/committing the completed 7A.2c.1 slice; no such action is performed by this checkpoint. Any later 7A.2c work needs a separately bounded task. Sprint 7A.3 reconstruction and downstream clinical reassessment remain deferred, not implied by graph resolution. Preserve the 549-test feature-state checkpoint and the established historical semantics.

## Normal development workflow

Use a focused feature branch from verified `main`, inspect applicable instructions and standards, implement a bounded change, run the full baseline plus relevant new checks, review the diff, then seek explicit approval before staging/committing/pushing or merging. Earlier history uses feature branches and PRs; recent foundation commits are directly on main. [CONTRIBUTING](../../CONTRIBUTING.md) does not yet formalize a workflow, so this is the default handoff convention, not a claim of branch-protection enforcement.

## Recovery instructions for a new session

1. Locate the actual Git repository (not a conversation mirror); read applicable `AGENTS.md` instructions and this file.
2. Inspect `git status --short --branch`, `git rev-parse HEAD`, `git log -10 --oneline`, remotes and any staged/unstaged changes. Preserve existing work; never reset to this checkpoint merely to match it.
3. Compare with the baseline above. If network access is available, fetch or inspect the remote before claiming live synchronization; do not overwrite divergent work.
4. Read the three standards, clinical-model implementation notes, current services and tests. Re-run the documented baseline; investigate differences before continuing.
5. Confirm the next phase and unresolved boundaries below, propose a bounded implementation, and report changed files, test results and limitations. Do not infer approval or completed capabilities from old chat messages.

## Known documentation gaps

[PROJECT_HISTORY](../00-governance/PROJECT_HISTORY.md) stops at the August architecture baseline and calls that version approved/frozen; it does not establish approval of the newer Draft standards. ARCH Section 26's retrieval-only implementation snapshot and references to SAFE as future work predate the current code/SAFE commit. DATA's candidate-parent hash is explicitly historical. For implementation scope, use the current code and clinical-model README.

Legacy taxonomy/lifecycle mappings, missing CAS-CDS-001 and mismatched ADR document references remain open in DATA Section 50.1 and SAFE Section 2. Do not silently rewrite legacy standards. The top-level README and contribution/security procedures are intentionally sparse; automated tests do not establish production readiness.

## Update this file when

- A major merge or milestone changes the stable baseline or implemented capabilities.
- Architecture, data or safety standard versions/statuses change.
- A verified test-baseline milestone changes counts, commands or setup requirements.
- The next development phase, deliberate deferrals or significant blockers change.

## Security

Never store secrets, credentials, tokens, patient-identifiable data or confidential clinical records in this document. Use synthetic examples and non-sensitive repository references; follow [SECURITY](../../SECURITY.md).
