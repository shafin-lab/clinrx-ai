RF2 ISOLATED SYNTHETIC HARNESS — REVIEW CANDIDATE

Authorized scope: in-memory validation and identity/lineage decisions only.
Contract: rf2-harness/v1-proposal.2, base 635cfe224a49b98d489c5b66c63a41010ee2bbb6
plus precedence addendum db33b852b203cda3ba721c77c873c944f10c738a.
Producer proposal 6fac1a26fc4f28d7128beea94d8c80f271383d83 remains a proposal;
passing harness fixtures does not authenticate an issuer or activate eligibility.

FILES
rf2_harness.py: standalone stdlib validator and resolver, no application imports.
schema.json: strict closed schema vocabulary interpreted by validate_shape;
not advertised as a general JSON Schema engine. Conditional structure checks are
explicit in validate(). Unknown identifier strings parse but remain unsupported.
contracts/: exact approved text, with addendum precedence.
original/: unchanged approved 24 payloads and 23 conditional design scenarios.
fixtures/derived/: 23 new strict run inputs, with synthetic scoped registry
snapshots; DERIVATION-MANIFEST.json records correspondence and changed expectations.
fixtures/edge/: separately identified added-edge fixture.
tests/: focused conformance and edge tests. Dynamic edge inputs/results are
captured with hashes in the separate evidence publication.
run_focused.py: focused runner with raw log, subprocess exit and source hashes.
fixture_support.py and generate_fixtures.py: synthetic input construction only.
No production adapter, persistence, clinical calculator or application integration.

RUN
Requires Python 3.11+ with IANA timezone data; pytest is a test dependency only.
With a chosen Python environment:
  python run_focused.py unique-run-name
A run name cannot overwrite prior logs. Only tests in this directory run.
For individual input evaluation (no file/database access by resolver):
  python rf2_harness.py < fixtures/derived/10-summary-known.json
Output is JSON decisions/reasons, never balance or production eligibility.
The CLI reads bounded stdin; schema is loaded from its adjacent checked file.

DECISIONS
Malformed shape, invalid interval structure and unsupported units reject the run.
Unsupported producer/profile strings remain semantic exclusions and participate
in identity conflict analysis. Registry resolution is cutoff, unique terminal,
then availability, with no convenient predecessor fallback.
Typed relations preserve known summary members and sequential drain collections.
Conflict components exclude affected candidates; unbounded dependency/registry
ambiguities withhold the scope. Withheld/rejected runs emit no candidate_include.
Exact replay collapses, correction selects one terminal, no status fallback.
Original decimal/timestamp spelling remains canonical content, not normalized.

EXPLICIT CONSERVATISM / LIMITATIONS
All registry types are scope-level required dependencies. An invalid/missing or
unavailable registry withholds the whole scope because the harness cannot prove
its effects are bounded. This is conservative; it does not infer independence.
No automatic source/profile eligibility, unit conversion, arithmetic subtotal,
clinical-as-of UI mode, coverage model, storage or durable command recovery.
Synthetic keys and assertions are assumptions under test, not physical truth.
Production-to-repository binding and durable registry retention remain deferred.

VALIDATION ATTRIBUTION
Initial focused run: 88 passed.
Expanded audit: 95 passed, 2 failed. Duplicate registry relationships were not
rejected; single-node revision self-cycle lacked a conflict-group diagnostic.
Both corrected; additional edge assertions added.
Corrected final focused run: 110 passed. See separate raw logs, JUnit, source hashes,
exact synthetic input/output captures and environment metadata.
No full application suite, hosted CI, browser, live database/server or installation
was exercised. Application code and running workspace were not modified.
Execution remains disabled. Results await Director acceptance.
