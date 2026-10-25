#!/bin/sh
# Launch only this candidate; never seed, migrate or copy the original preview store.
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TASK_DATABASE="$TASK_ROOT/runtime/infection-library/patient.sqlite3"
TASK_FRONTEND="$TASK_ROOT/review-evidence/infection-library/build-complete-ncdc"
TASK_PYTHON=${CLINRX_PYTHON:-/Users/mohammedshafiqshajahan/Documents/clinrx-ai/backend/venv/bin/python}
test -f "$TASK_DATABASE" || { echo 'Prepared candidate database is missing.' >&2; exit 1; }
test -f "$TASK_FRONTEND/index.html" || { echo 'Reviewed frontend build is missing.' >&2; exit 1; }
test -f "$TASK_ROOT/runtime/infection-library/patient.m10-signing.key" || { echo 'Candidate signing key is missing.' >&2; exit 1; }
cd "$TASK_ROOT"
exec env PYTHONPATH="$TASK_ROOT/backend" PYTHONDONTWRITEBYTECODE=1 \
  CLINRX_M10_DATABASE="$TASK_DATABASE" CLINRX_M10_FRONTEND="$TASK_FRONTEND" \
  CLINRX_M10_ORIGIN=http://127.0.0.1:5247 \
  "$TASK_PYTHON" -m uvicorn app.demo.transfusion_gateway:from_environment \
  --factory --host 127.0.0.1 --port 5247 --workers 1
