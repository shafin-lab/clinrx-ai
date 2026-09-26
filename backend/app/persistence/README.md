# Sprint 7A.1 — Persistence Foundation

Local, synthetic-data storage only. This implementation follows ARCH-001 v1.1,
DATA-001 v0.3 and SAFE-001 v0.2 (all Draft). It does not authenticate identity
assertions, establish clinical validity or authorize patient-care use.

## Scope and boundaries

Synchronous SQLAlchemy 2.0.54, file-backed SQLite and Alembic. Pydantic clinical
models are unchanged. The adapter contains all database dependencies; existing
knowledge APIs and release/presentation governance are unchanged.

Tables: `patient`, `encounter`, `fact_revision`, `repository_identity`, plus
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
Conditions, procedures, derived values, calculation executions and all correction
writes are also explicitly unsupported. A second revision of an existing stable
fact requires the future correction workflow, even without a supersedes link.
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
