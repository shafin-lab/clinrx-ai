# ClinRx AI — Project State and Recovery Checkpoint

Last verified: 2026-09-26. Operational handoff only; this is not an architecture standard.

## Purpose and stable baseline

ClinRx AI is a clinical decision-support platform being built around structured knowledge, patient context, traceable evidence, deterministic computation and governed AI assistance. It supports clinician judgment; the current repository is a development prototype, not an approved patient-care system.

- Stable `main` baseline: `9171597ee8d3eaaf10aabd07c6b1df02741c6bf2` — `add clinical release and presentation governance`.
- At checkpoint creation, the working tree was clean and local `main` and `origin/main` matched this commit. Reverify remote state when resuming; this is a dated checkpoint, not a moving branch pointer.
- **Git history, committed repository artifacts, current code and reproducible tests are authoritative over conversational memory.** This file is a navigation aid; resolve discrepancies from those artifacts and record the result.

## Test baseline

Verified at the baseline above: **181 passed**, using Python 3.11.6 and pytest 9.1.1. Coverage is in [retrieval tests](../../tests/test_retrieval_service.py), [clinical-model tests](../../tests/test_clinical_models.py) and [governance tests](../../tests/test_governance.py). Passing software tests is not clinical validation.

Run from the repository root, without generating bytecode or pytest cache:

```sh
PYTEST_ADDOPTS='-p no:cacheprovider' PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python -m pytest -q
git diff --check
```

The existing virtual environment is local setup, not a portable repository artifact. [Backend requirements](../../backend/requirements.txt) pin runtime dependencies but do not include pytest; a fresh session must establish its test environment explicitly rather than assume the environment already exists.

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

## Implemented capabilities

- [FastAPI application](../../backend/app/main.py): root status, `/knowledge`, `/knowledge/search`, and `/knowledge/{knowledge_id}`. Knowledge is loaded from two JSON objects in `knowledge/objects/`; search supports query/domain/status/object-class filtering and deterministic ranking.
- [Clinical models](../../backend/app/models/clinical/README.md): Pydantic contracts for patient/encounter context, seven fact categories, units/missingness, medication orders versus administrations, calculation execution provenance, immutable snapshots and bounded lineage checks.
- Separate candidate, rendering, safety-evaluation and human-decision records, with revision/content consistency checks and JSON round-trip coverage. Some derived properties intentionally remain Python-only; consult the implementation notes before designing APIs.
- [Governance service](../../backend/app/services/governance_service.py): pure release assessment/decision and presentation assessment/recording functions. Contracts bind exact payload, policy, context, authority, freshness, warning exceptions and final-delivery evidence; they record withheld, unconfirmed or rejected outcomes as appropriate.
- These functions consume supplied assertions. They do not authenticate producers, validate natural-language clinical meaning, inspect live patient systems, persist records or actually display content. No clinical-model/governance API is wired into the application.

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

- No clinical persistence, cross-request revision registry, durable audit/idempotency or historical resolver yet; local bundle validation is not database integrity.
- No live patient ingestion, authenticated assertion producers, revocation feeds, trustworthy-clock infrastructure or atomic display adapter.
- No clinical algorithms/rule engine, terminology/unit conversion service, FHIR mapping, medication reconciliation, governed evidence retrieval, external AI integration or clinical deployment validation.
- Frontend, mobile, infrastructure and CI workflow directories remain placeholders. Privacy/retention enforcement and operational recovery integrations are future work.

**Next planned phase: Patient Context + persistence** (direction set for this checkpoint, not a claim of completed implementation). Build on existing PatientContext/EncounterContext and snapshot contracts; first agree the ingestion/reconciliation, retained-reference resolution, immutable revision, authorization and audit boundaries. Select and implement persistence only through explicit design review; no database/provider is selected by this file. Preserve the 181-test baseline and add focused persistence/context regressions using synthetic data.

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
