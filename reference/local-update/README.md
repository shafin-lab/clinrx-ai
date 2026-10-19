# b419444 local workspace update

Source: b4194447829f060387b816437694af9f6c0cb60e. Origin: http://127.0.0.1:5195/.
The existing synthetic database/repository and same browser origin are preserved.
Previous frontend/runtime and an actual pre-update SQLite checkpoint are retained.
The older observation wrapper is stopped; it does not append this session to the
earlier milestone capture files. No production service/configuration is touched.

Initial startup needed the explicit PYTHONPATH=backend import path. Initial browser
load of the earlier compiled authoring bundle displayed Local authoring unavailable:
that bundle enabled VITE_SYNTHETIC_AUTHORING without VITE_SYNTHETIC_HOSTED. Compile
success in the earlier validation was not proof of a usable runtime authoring mode.
Both settings are now explicitly true in a fresh typecheck/build of unchanged b419444.
The earlier bundle remains in initial-misconfigured-build; logs and settings of the
corrected build are retained. The installed final assets are separately hashed.
No earlier published evidence is relabelled or replaced.

Fresh health reports execution_enabled=false. Each HTTP-served HTML/CSS/JS digest
matches the final installed build. The browser observes the corresponding asset
paths, renders the workspace with disabled-execution messaging and no console
warnings/errors. A read-only API snapshot contains 158 current items in the same
repository. These counts are distinct from 165 immutable stored fact revisions.
All 12 tables match between before/after SQLite checkpoints; both integrity checks
pass. Both retained receipts and prior records/notes/references are unchanged.
No new clinical evidence was written during this update/readiness check.

This establishes local update/load correspondence, not a new adversarial browser
exercise, clinician usability acceptance or M1 re-review verdict. The user will
perform the next complete synthetic journey without button-by-button coaching.
Production execution remains disabled; no merge, deployment or external hosting.
