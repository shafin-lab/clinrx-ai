# Persistence Foundation — Sprint 7A.1 through 7A.2c.1

Local, synthetic-data storage only. This implementation follows ARCH-001 v1.1,
DATA-001 v0.3 and SAFE-001 v0.2 (all Draft). It does not authenticate identity
assertions, establish clinical validity or authorize patient-care use.

## Scope and boundaries

Synchronous SQLAlchemy 2.0.54, file-backed SQLite and Alembic. Pydantic clinical
models are unchanged. The adapter contains all database dependencies; existing
knowledge APIs and release/presentation governance are unchanged.

Tables: `patient`, `encounter`, `fact_revision`, `revision_link`, `repository_identity`, `weight_trend_execution`, plus
Alembic's version table. Patient and encounter registrations are immutable through
the repository. Encounter ownership has a database foreign key; fact ownership
uses a composite foreign key to the encounter and its patient. Exact fact
references have a unique constraint. Repository identity namespaces ingestion
watermarks so unrelated database files cannot share an unqualified cutoff.

Supported facts: ClinicalObservation, MedicationOrder, MedicationAdministration,
ClinicalInference. Complete nested domain payloads are retained with exact
references, provenance/lineage, clinical time, verification and uncertainty.
Storage is not a declaration that these references resolve or are clinically
consistent across records. Read-only declared-lineage resolution is described below. Order/product cross-record
validation and clinical safety evaluation remain later responsibilities.

Concrete encounters are sufficient for this slice. Explicit longitudinal-context
writes fail with UnsupportedOperation; their domain contract is unchanged.
Conditions, procedures, derived values and calculation executions remain unsupported.
Root insertion uses append_fact; corrections use the explicit append_revision operation
described below. Retraction, invalidation and restoration remain unsupported. Missing
values, clinical status fields and correction reasons do not implement those lifecycles.
No reconstruction engine, standalone snapshot store, reverse graph lookup, patient endpoints,
presentation persistence, PostgreSQL adapter or production PHI handling is implemented.
Synthetic execution/decision recovery is separately scoped below.

## Canonical payload and mapping

Version 1 payloads are validated Pydantic JSON with sorted object keys, compact
separators, explicit defaults/nulls, UTF-8 text and no nonfinite numeric literals.
JSON key order and omitted defaults normalize to the same content. Array order,
Decimal lexical precision (including trailing zeros), timezone offsets and raw
source spellings are preserved, not normalized away. Numerically equivalent
quantities or equal instants with different retained representations may therefore
conflict; they are not silently substituted for the first source representation.
Idempotency therefore means equality of canonical retained representation, not
clinical/domain equivalence. JSON key order, omitted defaults and ordinary
Pydantic round-trips are idempotent; changed Decimal scale, equal instants with
different offsets, and reordered ingredient IDs conflict. The first retained
payload and ingestion metadata remain unchanged. Any future semantic-equivalence
comparator requires a separate, versioned design decision.
This is a versioned application format, not a claim of RFC canonical JSON.

Mappings revalidate inputs and loaded payloads. Decimal values are strings, never
SQLite floating-point values. Clinical timestamps retain their offsets inside
the payload. Before inserting a registration or fact, serialization recursively
checks original timestamps against their encoded/decoded wall time and offset.
Representations that payload version 1 cannot faithfully round-trip, including
seconds-bearing or fractional timezone offsets, raise UnsupportedOperation.
No timestamp is normalized; supported timestamps retain their original instants.
Failure aborts the surrounding transaction, including earlier writes. Indexed identity/target columns are generated from the validated
object and checked against it on load. Unknown values stay unknown. Unsupported
payload versions, invalid domain data and inconsistent envelopes fail explicitly.
Encounter registration/loading and scoped fact operations validate retained
parent registrations, including payload/key consistency, before trusting ownership.
SQL parameters are hidden from SQLAlchemy error formatting. Repository input
validation/serialization failures become payload-free PersistenceInputError;
stored decoding failures become StorageIntegrityError. Sensitive validation
exception chains are suppressed. These errors identify the operation/category,
not submitted clinical values. Callers must still avoid explicitly logging inputs.

Same exact reference and same canonical content returns the retained record and
original ingestion metadata. Changed content raises RecordConflict; changed
binding raises ScopeMismatch. No upsert overwrites a prior clinical payload.
Source identifiers are retained, not used for automatic patient matching/merging.
Unresolved binding assertions can be retained without promotion to verified status;
there is no verified-snapshot operation in this slice.

## Transactions and durability

Use `create_database(path)` and `with transaction(engine) as repository:`. Within
that block, register_patient/register_encounter, append_fact, load_patient,
load_encounter and load_fact perform explicit validated operations. Fact methods
require a ContextTarget; exact-reference lookup never falls back to another
revision or another patient/encounter. These scope checks are not authentication.

Methods flush but do not commit. Exiting the block successfully commits; failure
rolls back all writes. Even catching a repository error inside the block marks
the transaction failed. Returned records/cutoffs are provisional until successful
exit. Repository handles cannot be reused after closing the transaction.

Every connection enables and verifies foreign keys and sets synchronous=FULL.
Explicit BEGIN IMMEDIATE avoids sqlite3 legacy transaction behavior and serializes
read/check/write units in this local slice, including read-only repository units.
Contention times out after five seconds; errors are not silently retried. This
trades concurrency for a simple, consistent boundary. PostgreSQL will require
its own tested transaction/concurrency policy rather than inheriting SQLite SQL.
No create_all or implicit schema creation is used by the repository.

Repository-assigned UTC ingestion time is separate from source clinical times.
Fact ingestion_sequence uses SQLite AUTOINCREMENT; committed insertion positions
are not reused by normal append operations. Gaps are allowed. Retry retains the
original metadata. This is not a trusted-clock service or a commit timestamp.

RepositoryCutoff carries repository_id, fact_watermark and captured_at.
ReconstructionMetadata reserves an exact reconstruction-policy Reference
(including version), that repository cutoff, a knowledge cutoff and optional
clinical-as-of time. It has no default policy and does not run reconstruction.
The watermark bounds facts only; patient/encounter registrations are immutable
in this slice. Future mutable registration history needs its own versioning.
A clock time alone must not replace the fact watermark. Database copies/restores
retain repository identity; divergent copies must not be treated as one live
repository without a later recovery/fork policy. No retained-snapshot table is
prematurely introduced.

Immutability here is an application write boundary, not protection against a
privileged database editor. Authorized retention/deletion, restore eligibility,
production access controls and authenticated assertions remain future work.
Do not introduce real PHI. Keep database and journal files outside Git; use
synthetic fixtures and local storage, not a shared network filesystem.

## Reproducible setup and migration

Supported/tested baseline: CPython 3.11.6. Runtime dependencies remain in
backend/requirements.txt; requirements-migrations.txt adds Alembic and its
transitives; requirements-dev.txt adds pinned pytest and its transitives.
Greenlet is pinned explicitly because SQLAlchemy's dependency varies by platform.
No async database stack is used. Other Python/platform combinations require testing.

From the repository root:

```sh
python3.11 -m venv backend/venv
backend/venv/bin/python -m pip install -r backend/requirements-dev.txt
backend/venv/bin/python -m pip check
CLINRX_DATABASE_PATH=/absolute/local/path/synthetic.sqlite3 backend/venv/bin/python -m alembic -c backend/alembic.ini upgrade head
PYTEST_ADDOPTS='-p no:cacheprovider' PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python -m pytest -q
git diff --check
```

The database parent directory must already exist. CLINRX_DATABASE_PATH is required
for the migration CLI; no default patient-data path is selected. Use ordinary local
file paths. The repository rejects unknown/missing Alembic schema revisions.

Initial migration 7a1_0001 uses explicit reviewed DDL, independent of current ORM
metadata. Tests compare the migrated schema with metadata, run the CLI from a
different directory and verify a repeat upgrade is harmless. Offline SQL generation
and destructive downgrade are deliberately unsupported in this first slice; use a
new disposable synthetic database rather than delete retained history automatically.
Future migrations require review and preservation tests, including payload-format
compatibility. Pin updates require a fresh environment and regression verification.

## Limits of verification evidence

Thread-pool retry tests verify outcomes for concurrent submissions but do not force
lock overlap; they are not deterministic contention or multi-process stress tests.
The separate-process reader verifies committed close/reopen durability, not
interrupted-writer recovery or a commit-before-acknowledgement failure. Rollback
tests cover raised/caught operation failures; they do not simulate process/power loss.
Migration tests cover empty/repeated upgrade, CLI operation, inspected schema
alignment and rollback of one DDL operation, not every migration-failure recovery
path. Those additional recovery/contention scenarios remain deferred; this slice
makes no broader guarantee from these tests.


## Sprint 7A.2a — Immutable revision chains

append_revision(fact, target=...) requires an exact supersedes reference and a
correction reason. Revisions form one linear chain per (kind, id), permanently
bound to the same patient and encounter. Labels are opaque; ingestion sequence,
not numeric or lexical revision order, establishes insertion order. The predecessor
must already exist and be terminal for a genuinely new successor. Root insertion
remains append_fact; a second root is rejected. No historical/latest query API,
time filtering, lineage resolution or reconstruction is added.

Exact canonical retries return the original payload and ingestion metadata,
including retries of revision 2 after revision 3 exists. Retry comparison occurs
before terminal-predecessor enforcement. Changed canonical content conflicts.
Existing Decimal, offset, ordering, timestamp and sanitized-error policies remain
unchanged. Earlier revisions and metadata are never updated.

The additive revision_link table has a successor primary key, unique predecessor,
two fact-sequence foreign keys and predecessor < successor check. Repository
operations additionally validate the entire encountered stable-fact chain,
payload/link agreement and patient/encounter ownership, including links entering
or leaving the chain. Malformed chains fail on exact reads and writes. Validation
of revision links is not provenance/dependency traversal or clinical adjudication.

Migration 7a2_0002 follows the unchanged initial migration. Its local preflight
rejects unexpected multiple legacy revisions, correction records, noncanonical
JSON, envelope/ownership mismatch, invalid ingestion times, foreign-key violations,
invalid repository identity and invalid sequence allocation. It does not rewrite
payloads or infer old history. It is not a comprehensive clinical validator of
legacy data; normal validated loading remains required. Destructive downgrade
remains unsupported. Existing sequence gaps/high-water allocation are preserved.

The existing BEGIN IMMEDIATE policy serializes competing successors. A forced
lock-overlap regression verifies one successor commits and the competitor sees a
conflict. Revision and link insertion share the surrounding transaction, including
rollback when errors are caught. Restart tests retain exact historical references
and idempotent retries; no process-crash or power-loss guarantee is added.

## Sprint 7A.2b — Historical retrieval

The persistence-local `history.py` defines frozen query contracts and a frozen
`HistoryResult`. Results contain `cutoff`, `target`, a tuple of `StoredFact`
`records`, `selection` (`history` or `latest_known`), optional `identity`, and the
applied `clinical_filter` / `ingestion_filter`. Empty results are explicit empty
tuples; single-fact latest results contain zero or one record. Single-fact APIs
validate FactIdentity at their boundary; None cannot broaden their scope. They do not certify
clinical validity, source completeness or current applicability.

Repository operations (all transaction-scoped):

- `list_revisions(identity, target=..., cutoff=...)`: all visible revisions of a
  `FactIdentity(kind, id)`, ordered by ingestion sequence.
- `load_latest_known(identity, target=..., cutoff=..., clinical_filter=None,
  ingestion_filter=None)`: one terminal revision within the visible prefix.
- `list_history(target=..., cutoff=..., clinical_filter=None,
  ingestion_filter=None)`: scoped retained revisions.
- `list_latest_known(target=..., cutoff=..., clinical_filter=None,
  ingestion_filter=None)`: one visible terminal revision per stable fact.
- `load_current_latest_known(identity, target=..., ...)` and
  `list_current_latest_known(target=..., ...)`: capture a cutoff and invoke the
  same latest-known operations; results always return that explicit cutoff.

Every historical query validates repository UUID and a strict nonnegative
watermark no greater than the transaction-visible maximum. Gaps and zero are
valid prefixes. `captured_at` is retained metadata, not a substitute for the
watermark, a signature, or proof of historical wall-clock visibility. Results
obtained while writing are provisional until successful transaction exit.

Fact rows and revision links are bounded by the cutoff before chain validation
and selection. Only links whose successor is within the prefix are considered;
future corrections, future payload errors and future successor links do not
change old results. Visible payloads, metadata, chain structure and ownership
are validated before any filters are applied. Patient/encounter registrations
are validated as immutable scope prerequisites, not historically reconstructed.
Exact `load_fact` retains its existing full-chain validation and is not a
cutoff-aware API; use `list_revisions` for historical revision visibility.

All results are ordered by ingestion sequence, irrespective of revision labels,
equal timestamps or a backward wall clock. Latest-known selects the visible
terminal revision first and then applies both filters. An older matching revision
is never resurrected when the terminal revision does not match a filter.

`ClinicalTimeFilter(axis='event'|'effective', start=None, end=None,
include_unknown=False, include_imprecise=False)` requires at least one aware bound
and, when both exist, start < end by instant. Query windows are half-open
[start, end). Event filtering tests membership. Effective filtering tests overlap
with the retained inclusive effective endpoints (including start=end); a missing
end is treated as an open-ended recorded interval, not evidence of continuing
clinical applicability. No event/effective fallback is performed.

A missing selected timestamp or `precision='unknown'` is included only with
`include_unknown=True`, without inventing a timestamp. `day` / `approximate`
precision is excluded unless `include_imprecise=True`; that option compares the
retained representative timestamp/interval, not an invented uncertainty range.
Original precision, uncertainty and offsets remain in every returned fact. With
no clinical filter, history includes all times, including unknowns. Instant
comparisons use exact integer ordinal/time-of-day microseconds minus the UTC
offset, honoring DST folds without constructing a UTC datetime or using floating
point timestamps. This supports year-1/year-9999 offset boundaries without
rewriting retained data. Query bounds and ingestion filters use the same comparison.

`IngestionTimeFilter(start=None, end=None)` uses the same half-open interval and
is strictly subordinate to the already-fixed repository prefix. It filters
assigned ingestion timestamps; it does not mean committed or externally visible
by that time. There is no `as_of_commit_time` operation. In particular, backdating
an ingestion clock never makes a later sequence visible in an earlier prefix.

No schema or migration change is required. No lineage traversal, dependency
resolution, context reconstruction, retraction lifecycle or clinical adjudication
is introduced. Scoped retrieval currently loads and validates complete visible
chains in memory; indexing/pagination and large-history performance remain later
work. Queries do not persist results or mutate canonical payloads/metadata.


## Sprint 7A.2c.1 — Read-only durable lineage resolution

`resolve_lineage(reference, *, target, cutoff, limits)` accepts one exact domain
`Reference`, one explicit patient/encounter `ContextTarget`, a `RepositoryCutoff`,
and persistence-local `LineageLimits`. Obtain it through the existing transaction
context. It performs no writes. Existing write acceptance, canonical payloads,
schema, migrations, domain contracts and revision retries are unchanged.

The immutable `LineageResult` contains the root `reference`, validated `target`
and `cutoff`, `nodes` (retained `StoredFact` plus roles), `assertions`, expanded
`dependencies`, separate `associations`, `unresolved` references, retained
`provenance` disclosures, conservative `confirmations`, `coverage`, and immutable
exact-reference `ancestry` sets. All collections are tuples/frozensets. Roles are
`evidence`, `confirmation_validation`, and `association`; they may overlap.
The root is included in its ancestry. Association-only nodes have no analyzed
ancestry entry. Returned payloads are authorized scoped data, not sanitized logs.

Each `LineageAssertion` retains the original `LineageEdge`, including target,
basis order and rationale. Its identity is `(owner exact reference, ordinal)`.
`Dependency` uses that owner/ordinal and an optional `basis_ordinal`, with explicit
`source -> owner` direction. Confirmation basis expansion preserves declaration
order. `Association` identifies either an upstream `fulfills_order` edge or the
administration's `order` field. An order is never evidence of administration.
Method/model references remain artifacts inside the retained payload, not patient
evidence endpoints. Revision `supersedes` links are never dependency edges.

Visibility is established before graph extraction or validation. The resolver
validates the cutoff UUID/watermark and parent registrations, counts only scoped
rows at/below the watermark, then uses the existing unfiltered historical reader
to validate the visible prefix. It never calls unrestricted `load_fact`/`_chain`
or latest-known selection. All visible revisions are candidates; only exact
references resolve. A B that depends on A1 still depends on A1 after A2 exists.
No clinical-time or ingestion-time filter changes this graph. Clock reversal and
sequence gaps do not change visibility; captured_at is descriptive metadata.

The scope-wide historical reader validates all visible scoped records, including
records unrelated to the root. Thus unrelated *visible* malformed storage may
fail a query. Future payloads, revision links and lineage assertions are excluded
before validation, even if referenced by an earlier fact. Registrations retain
the existing immutable-parent semantics. This is scope isolation, not authentication.

A missing/out-of-scope/future exact ancestor has one indistinguishable reason:
`not_resolvable_in_scope_at_cutoff`. Unsupported kinds (including source_record
and derived_value) use `unsupported_reference_kind`. No out-of-scope/future lookup
is made to refine these reasons. Unresolved entries retain owner, role and ordinal
so separate assertions are not conflated. Missing roots fail with RecordNotFound;
visible malformed records fail safely rather than becoming unresolved. An ancestor
may arrive after its dependent: a newer cutoff can resolve it, while replaying the
old cutoff remains unchanged. No ingestion-order prerequisite is invented.

Iterative queue expansion collects dependencies and confirmation validation targets;
associations resolve their endpoints without expanding their lineage. An iterative
leaf-first topological reduction rejects self/circular evidence dependencies and
computes exact ancestry and the longest dependency path, including missing leaves.
Diamonds deduplicate nodes while preserving distinct assertions. Neither recursive
Python traversal nor revision-label sorting is used. Nodes/ancestry entries sort by
ingestion sequence; assertions and dependencies sort by owner sequence, edge ordinal
and basis ordinal. Associations sort by owner sequence, field and ordinal. Unresolved
entries sort by exact reference, role, owner and ordinal. Repeated cutoff queries
are deterministic, including reopening the repository in another process.

Origin checks preserve inferred/derived origin through the declared resolved graph;
observed/reported records cannot acquire inferred/derived evidentiary ancestry.
Unavailable external lineage remains an explicit limitation: the resolver cannot
detect undeclared copying or reconstruct the origin of an absent external record.
It does not rewrite origins, promote evidence, or perform clinical adjudication.

For independent_confirmation, basis references are evidence; the target and its
ancestry are visited for validation only. Shared exact ancestry or a shared stable
(kind, id) family invalidates the independence assertion. Family comparison does
not traverse revision history or substitute revisions. The confirmation must be
strictly later than a resolved target and no earlier than resolved basis records,
using the existing exact, overflow-safe integer instant comparator. Basis/rationale
structural requirements continue to come from the unchanged domain contracts.
Accepted confirmation assessments remain `unknown`, with
`independence_not_established`; missing ancestry adds
`unresolved_confirmation_ancestry`, and limited retained ancestry adds
`limited_declared_provenance`. There is no computed independent=True.

`result.support_relationship(left, right)` compares only analyzed closures in that
result. Shared exact or stable-family ancestry yields `dependent`; otherwise it
returns `unknown`. Inputs outside the analyzed set fail with a sanitized input
error. Disjoint IDs, absent ancestors, or successful graph resolution cannot prove
independence. No database query or reverse dependent lookup is performed.

Coverage is `partial` if any declared endpoint is unresolved, otherwise
`complete_for_declared_visible_graph`. This describes resolution of the visited
assertions, including association endpoints and confirmation validation ancestry;
it is not clinical/source completeness or a statement of independence. Retained
lineage classifications/limitations remain separately visible even with complete
resolution. Unrelated visible facts do not contribute assertions or limitations.

`LineageLimits()` defaults (also hard ceilings except depth's default):

| Budget | Default | Hard ceiling | Meaning |
| --- | ---: | ---: | --- |
| max_records | 10000 | 10000 | Scoped visible rows before history decoding |
| max_nodes | 1000 | 1000 | Distinct resolved nodes, including associations/targets |
| max_assertions | 10000 | 10000 | Expanded endpoints, including basis/target/association slots |
| max_width | 1000 | 1000 | Per-owner edge/basis slots plus administration order |
| max_depth | 100 | 1000 | Longest evidence path in edges, including missing leaves |
| max_ancestry_entries | 100000 | 100000 | Total stored closure memberships |

Budgets are strict integers; depth can be zero, other values must be positive.
Limit exhaustion raises payload-free `QueryLimitExceeded` and aborts the repository
unit even if caught; it never returns a truncated graph. These are graph/row budgets,
not a byte-size cap or wall-clock deadline for existing payload decoding. Scoped
historical validation still loads visible chains in memory. Large-history indexing,
pagination and payload-size governance remain later work.

Existing BEGIN IMMEDIATE gives one consistent SQLite unit for scan and traversal.
Results are provisional until transaction exit, including resolution alongside
writes. There is no separate lineage table or watermark: assertions are immutable
parts of their owner's payload and inherit its visibility. Endpoint visibility is
independently required. A later standalone-link API would need a new visibility
and immutability design; it cannot silently inherit this policy.

Reverse dependents, prospective write validation, external-source persistence,
cross-encounter reconciliation, clinical reassessment, invalidation/retraction,
reconstruction/snapshots, PostgreSQL, API/UI/auth and generalized graph services
remain deferred. No claim of production or clinical authorization is introduced.


## Sprint 7B.1 Phase 4 Increment 2 — immutable execution persistence

`executions.py` persists the existing `WeightTrendExecutionRecord` as a separate
workflow/decision artifact, never as a clinical fact or revision. The single
`weight_trend_execution` table contains execution_id, patient_id, encounter_id,
payload_version, canonical payload, payload_digest and ingested_at. Its UUID
primary key supports exact scoped lookup without an additional index. A composite
encounter/patient foreign key follows the existing ownership pattern; no cascading
delete, child tables, status column or execution revision links are introduced.

Public API:

```python
from app.persistence.executions import (
    append_weight_trend_execution, load_weight_trend_execution,
)

stored = append_weight_trend_execution(engine, execution_record, target=target)
recovered = load_weight_trend_execution(engine, execution_record.execution_id,
                                       target=target)
```

Each call owns its own SQLAlchemy session/transaction under the existing file-backed
SQLite connection policy. Call it outside the fact repository transaction. No session
is exposed, no fact operation joins this transaction, and there is no new transaction
composition API or coordination policy. A failure rolls back this call. This does not
make final context selection, governance decisions and execution persistence atomic.

Append accepts the reviewed typed record, revalidates nested contracts and scope,
checks the active repository UUID and validated registered patient/encounter ownership,
and writes only a new identity. Same UUID and identical canonical representation
returns the originally retained record and ingestion time; different canonical content
raises payload-free RecordConflict. Integrity of an existing in-scope row is checked
before retry comparison. A UUID collision in a foreign scope conflicts without decoding
that foreign payload. No UPDATE/upsert, replace or delete API is provided.

Both operations return frozen `StoredWeightTrendExecution(record, ingested_at)`.
The ingestion time is assigned by the adapter in UTC; callers cannot supply it.
It is not a clinical event/decision time or commit timestamp. There is deliberately
no fact ingestion sequence on an execution result. Execution insertion does not change
fact watermarks, historical prefixes, revision sequences or lineage-node membership.

Load filters by UUID **and patient and encounter before decoding**. Missing IDs and
foreign-scope IDs both raise the same RecordNotFound message, even when the foreign
payload is corrupt. Visible rows must pass execution payload-version checks, exact
SHA-256 verification over UTF-8 payload bytes, contract validation, canonical round-trip,
identity/scope/repository matching and UTC ingestion-metadata checks. Active ownership
registrations are also validated. Invalid visible storage raises StorageIntegrityError;
it never becomes ordinary withholding, an operational issue or a missing result.
Database/driver failures are sanitized as TransactionAborted; input and schema errors
retain existing payload-free categories with sensitive exception chains suppressed.

Execution payload version 1 is separately named from clinical payload version 1.
Existing canonical JSON rules retain Decimal scale, offsets, exact references and
array order. The digest detects corruption/inconsistency; it is not authentication,
a signature or protection from privileged database editing. Application immutability
likewise does not prevent direct privileged SQL edits.

Recovery returns the recorded historical content, including released, withheld,
operational-failure and permitted partial-evidence records. Deserialization validates
stored structural/decision consistency using retained evidence and times; it does not
invoke current selection, lineage resolution, authorization/freshness producers, final
recheck or a new release decision. Recovery does not reauthorize clinical use.

Migration `7b1_0003` is the additive successor to `7a2_0002`. Explicit DDL creates
only this table; repository identity, clinical payload version, existing bytes and
SQLite fact allocator are preserved. Repeated upgrades are harmless. Destructive
downgrade remains refused. Tests cover populated upgrade and injected post-DDL rollback;
they do not establish process/power-loss or commit-before-acknowledgement recovery.

Increment 4+ retains protected final re-selection, terminal lookup, final governance
orchestration, correction races and commit/recovery sequencing. The shared transaction
primitive is provided by Increment 3 below. No API, presentation/delivery, reassessment, reverse index or generic
workflow/audit/unit-of-work framework is added. Synthetic local use only.


## Sprint 7B.1 Phase 4 Increment 3 — shared transaction boundary

```python
from app.persistence.shared_transaction import execution_transaction

with execution_transaction(engine) as tx:
    repo = tx.repository
    executions = tx.executions
    stored = executions.append(execution_record, target=target)
    recovered = executions.load(execution_record.execution_id, target=target)
# Only successful context exit establishes commit.
```

The frozen facade exposes two fixed adapters, backed by one private SQLAlchemy
Session, one connection transaction and one BEGIN IMMEDIATE writer reservation.
Schema validation occurs before yielding. Adapters explicitly flush writes but do
not commit or independently roll back. The outer context owns completion. Returned
records and cutoffs remain provisional until successful exit.

One private active/failed/closed lifecycle guards both adapters before validation
or SQL. Every exceptional adapter failure poisons the shared transaction, including
missing required records, scope/content conflicts, invalid input, malformed stored
payloads, query limits, SQL errors and internal programming errors. Catching an
exception does not restore usability: both adapters reject subsequent calls without
SQL, and normal block exit raises TransactionAborted and rolls back. Process-control
exceptions mark failure and propagate unchanged. Both handles close after success,
rollback or failed completion; returned immutable values remain inspectable.

Normal typed negative results (empty history or unresolved lineage) do not poison.
A valid withheld or operational-failure execution record is ordinary persisted data,
not an adapter failure. Identical canonical retries recognize both committed rows
and rows flushed earlier in this same transaction, validate retained integrity, and
retain the original ingestion time. Changed content conflicts. Execution inserts do
not advance the clinical fact watermark or enter history/lineage.

The shared operation boundary preserves safe persistence error categories, suppresses
sensitive exception chains, and maps SQL/unexpected internal failures to payload-free
TransactionAborted errors before the caller can catch them. Legacy transaction(engine)
retains its existing internal-exception propagation policy. Standalone execution
append/load retain their Engine-only ownership and reject Session/Connection objects.

Contexts are synchronous and confined to their calling thread/process. They must not
be stored globally or reused. Separate contexts never implicitly join. Use the two
shared handles for atomic work; do not nest standalone execution calls. Independent
nested writers against the same SQLite file contend under BEGIN IMMEDIATE. A caught
failure in an independent inner transaction does not poison the outer context;
an exception escaping the outer block does roll it back. No ambient registry,
propagation, savepoints or asynchronous/distributed transaction behavior is provided.

Completion errors close both handles and raise TransactionAborted with
"transaction completion could not be confirmed". Cleanup attempts rollback where
possible; a commit exception does not prove nothing committed. Do not treat flushed
results as durable or persist a failure record inside the poisoned transaction.
Commit-outcome reconciliation remains Increment 4+.

Focused tests use real SQLite, SQL/transaction event observation, a separate read
observer without the application BEGIN IMMEDIATE hook, and zero-timeout competing
writers. They cover bidirectional rollback, caught failures, validation, privacy,
post-exit rejection, idempotency, visibility and injected completion failures. This
is not process/power-loss recovery evidence or a final clinical release workflow.
No schema, migration, execution contract, governance or selection change is involved.
