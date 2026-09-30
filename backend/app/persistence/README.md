# Persistence Foundation — Sprint 7A.1 and 7A.2a

Local, synthetic-data storage only. This implementation follows ARCH-001 v1.1,
DATA-001 v0.3 and SAFE-001 v0.2 (all Draft). It does not authenticate identity
assertions, establish clinical validity or authorize patient-care use.

## Scope and boundaries

Synchronous SQLAlchemy 2.0.54, file-backed SQLite and Alembic. Pydantic clinical
models are unchanged. The adapter contains all database dependencies; existing
knowledge APIs and release/presentation governance are unchanged.

Tables: `patient`, `encounter`, `fact_revision`, `revision_link`, `repository_identity`, plus
Alembic's version table. Patient and encounter registrations are immutable through
the repository. Encounter ownership has a database foreign key; fact ownership
uses a composite foreign key to the encounter and its patient. Exact fact
references have a unique constraint. Repository identity namespaces ingestion
watermarks so unrelated database files cannot share an unqualified cutoff.

Supported facts: ClinicalObservation, MedicationOrder, MedicationAdministration,
ClinicalInference. Complete nested domain payloads are retained with exact
references, provenance/lineage, clinical time, verification and uncertainty.
Storage is not a declaration that these references resolve or are clinically
consistent across records. Lineage resolution, order/product cross-record
validation and safety evaluation remain later responsibilities.

Concrete encounters are sufficient for this slice. Explicit longitudinal-context
writes fail with UnsupportedOperation; their domain contract is unchanged.
Conditions, procedures, derived values and calculation executions remain unsupported.
Root insertion uses append_fact; corrections use the explicit append_revision operation
described below. Retraction, invalidation and restoration remain unsupported. Missing
values, clinical status fields and correction reasons do not implement those lifecycles.
No reconstruction engine, retained snapshots, graph traversal, patient endpoints,
release persistence, PostgreSQL adapter or production PHI handling is implemented.

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
