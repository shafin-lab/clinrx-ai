# ClinRx AI

ClinRx AI is an AI-powered clinical decision-support platform. This repository contains the product's applications, shared code, infrastructure, and governed documentation.

## Repository layout

- `backend/` — backend services and APIs
- `frontend/` — web application
- `mobile/` — mobile applications
- `shared/` — shared libraries and types
- `infrastructure/` — deployment and cloud configuration
- `docs/` — product, clinical, technical, regulatory, and business documentation
- `assets/` — brand assets, diagrams, and screenshots
- `scripts/`, `tests/`, `tools/` — development support resources

## Status

Synthetic engineering demonstration implemented through M6.5: protected patient-state
and microbiology/antimicrobial review, exact provenance and explicit reconciliation.
It is not clinically validated or ready for production patient care.

Baseline: `608888824e83e39569beaa9f1053c39cb4a943fa`; schema head: `m6_0007`.
H1-A adds reproducible CI and a current checkpoint only. H1-B/C/D are planned;
M7 is proposed, not implemented.

See the [project checkpoint](docs/00-project/CLINRX-PROJECT-STATE.md),
[H1-A validation instructions and evidence](docs/07-testing-validation/H1-A-VERIFICATION.md),
[synthetic API instructions](backend/app/api/README.md) and
[frontend instructions](frontend/README.md).

## Reproducible validation

Use Python 3.11.6 and Node.js 22.13.0. From the repository root:

```sh
python -m venv /tmp/clinrx-validation
/tmp/clinrx-validation/bin/python -m pip install -r backend/requirements-dev.txt
PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 /tmp/clinrx-validation/bin/python -m pytest -q -p no:cacheprovider tests
PYTHONPATH=backend /tmp/clinrx-validation/bin/alembic -c backend/alembic.ini heads
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

CI uses separate Ubuntu 24.04 jobs, read-only permissions and official Actions pinned
to commit SHAs. Triggers are pull requests to main, pushes to main and manual dispatch.
Logs record actual checkout SHA and runtime versions; a pull-request checkout may be
a synthetic merge commit. No production secrets or deployment steps are configured.
A production build is validation only, not deployment approval.
