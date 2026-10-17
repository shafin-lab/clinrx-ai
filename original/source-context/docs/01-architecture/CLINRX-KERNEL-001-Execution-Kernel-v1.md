# CLINRX-KERNEL-001 — Execution Kernel v1

Version: 1.0. Recorded: 2026-10-04.
Status: engineering baseline freeze for synthetic development, not clinical approval.
Canonical baseline: `d52efb2b0d1759e432bf902cf5e3e65472c7e7aa`.

## Purpose and authority

Preserve the proven semantics of the first protected synthetic execution path while
allowing another capability to test reuse. Freeze means invariants must not regress;
it does not permanently freeze class names, module layout or extension interfaces.
ARCH-001 v1.1, DATA-001 v0.3 and SAFE-001 v0.2 remain Draft. This implementation
checkpoint does not amend them or claim production conformance.

Phase 4 is complete through explicit commit-outcome reconciliation. The previously
validated baseline is 1,250 full-suite and 701 weight-trend tests. These are historical
validation results, not tests rerun for this documentation change. See the
[checkpoint](../00-project/CLINRX-PROJECT-STATE.md) for focused counts.

## Layers and extension boundaries

| Layer | Existing implementation | Classification |
|---|---|---|
| Clinical contracts | `models/clinical/common.py`, `facts.py`, `decisions.py` | Extensible contracts; immutable references, explicit origin and uncertainty remain invariant |
| Durable facts | `persistence/repository.py`, `mapping.py`, `entities.py` | Reusable for supported observations, orders, administrations and inferences; encounter scope only |
| Historical visibility | `persistence/history.py`, `metadata.py` | Reusable repository-prefix semantics |
| Durable lineage | `persistence/lineage.py` | Reusable exact declared graph with finite budgets |
| Transaction lifecycle | `persistence/shared_transaction.py` | Reusable ownership/poisoning mechanism; current execution adapter is weight-specific |
| Governance | `models/clinical/governance.py`, `services/governance_service.py` | Reusable contracts and pure decisions over supplied evidence |
| Durable execution | `persistence/executions.py`, weight execution table | Weight-specific implementation of reusable durability principles |
| Protected execution/recovery | `execution/weight_trend_workflow.py` | Weight-specific request, composition, marker and reconciliation projection |

The existence of a domain type does not imply persistence support for it. In
particular, this baseline does not persist all seven domain fact categories.
ClinicalInference, history/lineage APIs, governance contracts, transaction
composition and persistence mechanisms may evolve compatibly with the invariants.

## Frozen invariant map

| ID | Invariant | Primary evidence |
|---|---|---|
| K01 | Exact clinical fact revisions are immutable | repository/mapping; persistence tests |
| K02 | Corrections form linear stable-identity chains with reasons | revision links; revision-chain tests |
| K03 | Repository UUID plus watermark defines historical visibility; timestamps do not substitute for it | history; historical-retrieval tests |
| K04 | Select the terminal visible revision before capability filtering | history plus selector; weight tests |
| K05 | Historical exact references are never silently replaced by later revisions | history/lineage; inference tests |
| K06 | Durable lineage preserves declarations, roles and conservative ancestry; disjoint ancestry does not prove independence | lineage tests |
| K07 | One shared Session, one BEGIN IMMEDIATE, one completion owner and shared poisoning; caught adapter failure cannot commit | shared-transaction tests |
| K08 | Handles are invalid after exit or poisoning, before further validation/SQL | shared-transaction tests |
| K09 | Completion uncertainty is explicit, never proof of commit or rollback | TransactionCompletionUnknown; workflow/reconciliation tests |
| K10 | Execution identity/content are immutable | execution persistence tests |
| K11 | Retained execution payload is canonical and digest-checked | execution persistence corruption tests |
| K12 | Execution recovery is scoped and historical; foreign rows are not decoded | execution persistence/reconciliation tests |
| K13 | Same execution ID and exact protected request recover the retained result | workflow/reconciliation tests |
| K14 | Same in-scope ID with different request conflicts | workflow/reconciliation tests |
| K15 | Reconciliation performs no current clinical recomputation | reconciliation spies and SQL tests |
| K16 | Governance release/withhold derives from explicit supplied runtime evidence | governance tests |
| K17 | Hard safety failures and required-check unavailability cannot silently become approval | governance/safety tests |
| K18 | Released, withheld, failed, uncertain, reconciled and delivered remain distinct | contracts/workflow/reconciliation tests |
| K19 | Execution insertion never advances the clinical fact watermark | execution persistence/shared-transaction tests |

Canonical retries preserve Decimal scale, timestamp offsets, source spelling and
array order under existing domain semantics. Digests detect inconsistency; they
are not authentication or protection against privileged rewriting.

## Execution lifecycle

```text
registered synthetic context + immutable observations
  -> input repository cutoff -> terminal-visible selection -> exact comparison
  -> inferred ClinicalInference -> fact persistence -> output cutoff
  -> exact durable lineage
  -> protected execution transaction:
       scoped retry lookup first
       matching retained row -> return after boundary exits
       absent -> replay historical evidence -> protected final cutoff/recheck
              -> snapshot/candidate/rendering -> safety/fidelity/context/dependencies
              -> fresh synthetic authority/runtime -> assess_release -> decide_release
              -> immutable execution append
  -> successful transaction completion -> return retained released/withheld record
```

Observation/inference persistence precedes the protected release transaction; this
is not one transaction encompassing all stages. Final recheck preserves the original
comparison/inference and feeds changed context into governance rather than rewriting
historical evidence or fabricating a safety failure.

```text
acquire Session/BEGIN IMMEDIATE -> active -> completion -> closed
                               -> adapter failure -> poisoned -> rollback/closed
completion acknowledgement fails -> closed + TransactionCompletionUnknown
later explicit reconcile -> committed_match | absent | exception
```

Adapters neither commit independently nor recover a poisoned unit. Results produced
inside the context are provisional. Process-control exceptions propagate with cleanup.
The existing SQLite hook also reserves a writer for standalone reconciliation reads;
no application DML is performed, but lock contention can fail the lookup.

## Outcome meanings

| Concept | Meaning |
|---|---|
| Released | Retained governance permitted this exact historical synthetic output; no delivery claim |
| Withheld | Completed negative governance decision, eligible for durable storage and reconciliation |
| Failed | Operational/integrity failure; protected workflow aborts without automatically inserting a failure record |
| Uncertain | Completion acknowledgement unavailable; commit may or may not have occurred |
| Reconciled committed match | A subsequent scoped load validated the retained protected request; no current authorization or invocation attribution |
| Reconciled absence | No retained row under the supplied ID/scope was visible during that lookup; not proof it never existed |
| Delivered | Separate presentation/destination evidence; no delivery adapter is implemented |

A valid standalone operational-failure envelope is recoverable through the general
weight loader but does not establish protected-workflow completion. Reconciliation
conflicts on incompatible identity, raises on visible corruption/read failure, and
never translates those failures into absence. Explicit execution retry after absence
checks again; new evaluation may reflect changed facts. No automatic retry exists.

## Capability-specific compatibility surface

Keep WeightTrendSelectionPolicy, exactly-two weight cardinality, kg-only acceptance,
RecordedWeightComparison, weight inference wording, candidate/rendering/safety/fidelity
producers, lineage witness, final recheck, WeightTrendExecutionRecord, protected
workflow, request projection and synthetic weight authorization specialized.
Their historical records and v1 behavior remain compatibility commitments; none is
advertised as a generic kernel contract.

## Experimental and absent production capabilities

Synthetic authority is not authentication. SQLite file-backed serialization is a
local policy, not a distributed/multi-node guarantee. There is no production
identity/authorization system, PHI security boundary, real laboratory integration,
heterogeneous terminology normalization or delivery/presentation adapter. In-memory
presentation contracts exist but do not prove actual display. Passing tests is not
clinical validation or deployment approval. Error sanitization suppresses standard
formatted chains; Python exception context remains introspectable.

## Next capability

Follow the [extension guide](CLINRX-KERNEL-002-Capability-Extension-Guide.md) and
[creatinine specification](../02-clinical-standards/CLINRX-CAP-001-Synthetic-Serum-Creatinine-Trend.md).
No production extraction is required before its selection/inference phases. Before
its durable execution phase, a small adapter-composition extension must preserve
K07–K09 while leaving the weight API unchanged. No registry or generic workflow is implied.
