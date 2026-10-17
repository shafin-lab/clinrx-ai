# H1-A — Reproducible CI checkpoint verification

Inspected 2026-10-15 (Asia/Calcutta), in the authenticated ClinRx cloud workspace.
No local Mac was used. H1-A changes only the CI workflow and three documentation files.

## Source and environment evidence

- Verified remote main and checkout baseline: `608888824e83e39569beaa9f1053c39cb4a943fa`
  (merge PR #18). Starting working tree was clean.
- Branch: `feature/h1-a-reproducible-ci-checkpoint`. HEAD remains the baseline;
  H1-A is unstaged/uncommitted, so no H1-A commit SHA exists yet.
- Corrected guard blob: `a05ead216b28448c8ec377544c1a0573a853aad2`.
- Local verification OS: Debian GNU/Linux 13, x86_64. This is not the GitHub runner.
- CI runner: Ubuntu 24.04. Python: 3.11.6. Node: 22.13.0 (npm 10.9.2).
- Dependencies: unchanged pinned backend requirement files and frontend package-lock.json.
  Backend used a fresh virtual environment; frontend used npm ci under Node 22.13.0.
- Schema head: `m6_0007 (head)`, checked via Alembic without applying migrations.

Each CI job prints actual `git rev-parse HEAD`, event, source SHA, ref, OS,
architecture, runner image version and runtime/tool versions. The actual checkout is authoritative: on a
pull request it can be GitHub's synthetic merge SHA rather than the branch-head SHA.
Dependency manifest SHA-256 digests are printed alongside the source SHA.
Logs contain no secret/environment dumps. No production secret or deployment is used.

## Workflow and official Action pins

Triggers: pull requests to main, pushes to main and manual dispatch. Separate backend
and frontend jobs use Ubuntu 24.04. Workflow permissions are contents: read;
checkout does not persist credentials. No cache restoration replaces clean installs.

| Official Action | Verified upstream tag | Commit SHA |
|---|---|---|
| actions/checkout | v4.2.2 | `11bd71901bbe5b1630ceea73d27597364c9af683` |
| actions/setup-python | v5.6.0 | `a26af69be951a213d495a4c3e4e4022e16d87065` |
| actions/setup-node | v4.4.0 | `49933ea5288caeca8642d1e84afbd3f7d6820020` |

Pins were verified using git ls-remote against each official actions repository's
exact tag. Reverify when changing a pin; do not replace these with floating tags.
The official actions/python-versions manifest also lists a Python 3.11.6 Linux
Ubuntu 24.04 x64 distribution (release 3.11.6-11113179737), confirming the requested
setup-python runtime is available for the selected CI runner. The local Python
3.11.6 interpreter was installed separately for cloud compatibility testing.
Workflow syntax was checked locally with actionlint 1.7.7 (exit 0, no findings).

## Reproduce from repository root

Use Python 3.11.6 and Node.js 22.13.0; choose a new disposable virtual-environment path.
Record `git rev-parse HEAD` and `git status --short` before running these commands.

```sh
python --version
node --version
npm --version
python -m venv /tmp/clinrx-h1a-validation
/tmp/clinrx-h1a-validation/bin/python -m pip install -r backend/requirements-dev.txt
/tmp/clinrx-h1a-validation/bin/python -m pip check
PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 /tmp/clinrx-h1a-validation/bin/python -m pytest -q -p no:cacheprovider tests
PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 /tmp/clinrx-h1a-validation/bin/alembic -c backend/alembic.ini heads
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
actionlint .github/workflows/ci.yml
git diff --check
git status --short
```

Expected changed-file inventory (include untracked files, since git diff alone omits them):

1. `.github/workflows/ci.yml`
2. `docs/07-testing-validation/H1-A-VERIFICATION.md`
3. `docs/00-project/CLINRX-PROJECT-STATE.md`
4. `README.md`

No application code, tests, clinical contracts, governance implementation, persistence,
migrations, schemas, dependency manifests or lockfiles may change under H1-A.

## Current validation results

| Check | Exact result |
|---|---|
| Full backend, Python 3.11.6 | 3494 passed, 1 warning in 356.33s (0:05:56) |
| Additional baseline run, Python 3.12.14 | 3494 passed, 1 warning in 314.35s (0:05:14) |
| Clean backend install / pip check | Exit 0; no broken requirements found |
| Node 22.13.0 / npm 10.9.2 clean install | Exit 0; 108 packages added in 3s |
| Full frontend tests | 3 test files, 60 tests passed; duration 5.99s |
| TypeScript typecheck | Exit 0 |
| Production build | Exit 0; Vite 8.3.4, 26 modules; build phase 135ms |
| Schema head | m6_0007 (head) |
| Workflow syntax | actionlint 1.7.7, exit 0, no findings |
| Action SHA verification | All three official tags match the pinned SHAs above |
| git diff --check | Exit 0, no output |
| Source inventory / staging | Exactly the four authorized files; index unchanged |

The backend warning is StarletteDeprecationWarning: using httpx with
starlette.testclient is deprecated; the library recommends httpx2. Dependencies
remain unchanged under the authorized scope. No test failures remain.

These runs cover the baseline's unchanged application, tests and dependencies.
Final documentation/workflow edits were checked separately with actionlint,
relative-link verification, diff whitespace checks and exact file inventory.

## Remaining limitations and phase boundary

Local verification does not establish a successful GitHub-hosted run. No workflow
was dispatched, published or deployed during this task. Ubuntu 24.04 execution and
GitHub run URLs remain pending separately authorized publication. Runtime versions
are fixed but hosted runner images can change; CI logs capture their OS/runtime state.

Historical full backend validation of the guard correction was 3,494 passed with
1 Starlette/httpx deprecation warning; it is not a new H1-A run. Software tests are
not clinical validation or production authorization. See the
[project checkpoint](../00-project/CLINRX-PROJECT-STATE.md) for clinical limitations.
H1-B/C/D remain planned and require separately approved scopes. M7 is proposed, not
implemented. H1-A does not start any of them or change GitHub settings.
