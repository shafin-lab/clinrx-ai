# CLINRX-KERNEL-002 — Capability Extension Guide

Version: 1.0. Date: 2026-10-04. Engineering guide for synthetic development.
Baseline: `d52efb2b0d1759e432bf902cf5e3e65472c7e7aa`.
Read the [Kernel v1 invariant map](CLINRX-KERNEL-001-Execution-Kernel-v1.md) first.

## Reuse unchanged initially

Use existing ClinicalObservation/ClinicalInference, exact Reference, provenance,
patient/encounter binding, canonical fact persistence, immutable revision chains,
repository cutoffs, history and durable lineage. Use ContextSnapshot, claims,
recommendations, rendering, safety/fidelity/context/dependency/authorization contracts,
RuntimeState, GovernancePolicy, assess_release and decide_release.

These contracts validate supplied evidence; they do not authenticate its producers,
interpret arbitrary prose or provide terminology, source integration or clinical approval.
Do not broaden persistence's supported categories merely because the domain has a type.

## Define explicitly for each capability

- Intended use, concept identity, accepted units and precise clinical-time meaning.
- Eligibility, source availability, missing/conflicting-data behavior and distinctness.
- Cardinality, ordering, comparison fields and allowed outputs.
- Exact inference method/version, evidence edges, grammar and disclosures.
- Candidate/rendering, independent safety/fidelity checks and versioned rule identities.
- Context/dependency producers, material-change policy and bounded synthetic authority.
- Typed request, retained evidence/lineage witness if needed, execution envelope,
  protected workflow identity and canonical reconciliation request projection.

Never import weight selectors, comparison fields, witnesses, grants or producer IDs
as supposedly generic clinical behavior. The first consumer must not define policy
for the next simply because their algorithms look similar.

## Durable extension point

Initially retain capability-specific execution records, adapters and tables. Preserve
canonical JSON, digest, version, scope, ownership, original ingestion metadata and
immutable retry/conflict semantics. A new table requires a separately reviewed
additive migration; do not rewrite historical weight payloads. Across tables, do not
claim database-enforced global execution-ID uniqueness; use capability-qualified
identity at any future shared caller boundary.

Before the second durable workflow, minimally separate transaction ownership from
concrete adapter construction. Reuse the same private Session, lifecycle and BEGIN
IMMEDIATE; preserve the public weight API. No raw Session/Connection exposure,
adapter registry, generic UnitOfWork, ambient propagation or independent adapter commit.
Do not duplicate transaction poisoning/completion ownership in a second implementation.

Reconciliation remains a narrow capability-specific API around durable scoped lookup
and exact request matching. No current clinical reads, clock, governance rerun or
automatic execution. Missing/foreign rows are absence; valid incompatible content
conflicts; corruption/read failure raises. An explicit retry after absence checks again.

## Required integration evidence

| Area | Expected tests |
|---|---|
| Clinical policy | Independent expected values; units, timing boundaries, distinctness, exclusions, conflicts and cardinality |
| Exact evidence | Terminal-before-filter, no resurrection, exact refs, same-ref contradiction and historical replay |
| Inference/lineage | Grammar and origin; ordered edges; correction pinning; malformed/unresolved graph behavior |
| Governance | Closed meaning, complete disclosures, negative evidence, required-check failures, release/withhold |
| Durability | Scope-before-decode, digest/version/envelope checks, exact retries, corruption, immutable results and reopen/process recovery |
| Protected execution | Correction races, one connection/transaction, failure poisoning, no success before completion |
| Reconciliation | Both commit-uncertainty outcomes, no DML/recomputation, privacy, errors and explicit retry after absence |

Run existing kernel and weight regressions unchanged. Do not duplicate their entire
matrices for each capability. Mirror only capability-dependent integration scenarios;
extract shared storage fixtures or a small adapter test matrix when two concrete
adapters justify it. Test count alone is not evidence of a correct clinical contract.

## When kernel changes are justified

A change must identify an actual second-consumer need, the invariant preserved,
compatibility impact, independent acceptance tests and migration implications.
Prefer a small function/validator or private transaction seam over a framework.
Keep domain semantics in the capability. Exactly-two selection, materiality rules,
clinical freshness and inference wording are not universal invariants.

Do not pre-create a TrendEngine, ClinicalWorkflow base class, selector framework,
comparison DSL, execution registry, generic rule engine, task DAG, conversion platform,
terminology service, recovery daemon or delivery queue. Reverse lineage, external
source graphs and reassessment need separate demonstrated requirements.

## Current next step

Implement only the separately authorized phases of
[CLINRX-CAP-001](../02-clinical-standards/CLINRX-CAP-001-Synthetic-Serum-Creatinine-Trend.md).
Phase A is selection/comparison; Phase B is inference with existing fact persistence
and lineage validation. Neither requires the later execution table or transaction
extension. A specification does not itself authorize implementation or clinical use.
