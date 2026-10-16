# ClinRx local ABG and broader echo demo validation

The local working changes expand hosting-preparation base `28496c4`. No new
commit, push, merge or deployment has been made. `source-identity.json` records
the base head, branch and SHA-256 of every modified/untracked source file.
Prior Director acceptance does not extend to this new expansion automatically.

## Changes

- 41 source records, 14 populated of 15 supported evidence families. HPI absent
  by default; explicit optional-HPI fixture coverage also passes with 42 records.
- Seven ABG/haemoglobin values with exact quantities, arterial specimen,
  collection timestamp and source-recorded FiO2, ventilation mode and PEEP.
- Twelve echo records, including RVSP/PASP estimates, TR velocity, RV size and
  function, septal/valve/pericardial findings, PH source wording, LVOT VTI and EF.
- No PH/PAH diagnosis, acid–base interpretation, calculated pressure estimate,
  new eligibility rule or treatment recommendation. Historical oxygen facts omit
  absent new context and retain canonical serialization compatibility.

## Evidence

- `backend-0.log/json`: complete backend regression command/result: **4,245 passed**,
  one existing Starlette/httpx warning, 637.39 seconds (640.26 seconds including process overhead).
- `frontend-pinned-0.log/json`: **447 frontend tests passed** under Node 22.13.0/npm 10.9.2.
- `frontend-pinned-1.log/json`: typecheck passed.
- `frontend-pinned-2.log/json`: default build passed.
- `frontend-pinned-3.log/json`: build passed with VITE_SYNTHETIC_HOSTED=true; local build
  only, no deployment. Earlier `frontend-*` files record Node 24 preliminary checks.
- `static-*`: dependency consistency, migration head, whitespace validation.
- `live-state.json`: response from actual loopback API; ephemeral signed read
  context replaced with a placeholder.
- `live-verification.json` and `verify_live.py`: independent stored-payload/API
  equality for all 41 facts, repository/cutoff correspondence, disabled gate,
  two matching retained outcomes and unchanged rows in all 12 database tables
  before/after those API reads. This is an API-read check after browser browsing,
  not a before/after capture of the entire browser session.
- `released_example.json` and `withheld_example.json`: actual retained responses
  from the fresh disposable case, generated only during explicit fixture setup.
- Browser DOM/screenshot captures demonstrate expanded echo, ABG context, empty
  optional HPI, two retained monitor revisions and the withheld receipt.

The browser exercised the actual API on 127.0.0.1:8766 through the existing local
workspace on 127.0.0.1:5179. API logs confirm state, history and retained lookup
responses. No new prepare/execute action was used during browser verification.
The fresh database and server logs are in sibling `abg-echo-local-run/`; the
previous `comprehensive-demo-local-run/` database/captures were preserved.

## Scope and limits

Production/API execution configuration, inference/execution modules, migrations,
dependencies, gateway code and deployment files are unchanged. The display checks
execution_enabled=false before browsing. No external HTTPS, hosted CI, new Linux
container validation or clinical readiness is claimed. The local servers remain
running for the user; all data is fabricated. Tests cover absent/mixed-venous
sample context so ABG settings cannot be substituted silently.

Field-selection references (no guideline thresholds imported):
[ASE right-heart/PH guidance](https://www.asecho.org/guideline/right-heart-in-adults-pulmonary-hypertension/)
and [AARC blood-gas guidance](https://www.aarc.org/wp-content/uploads/2025/03/davis-et-al-2013-aarc-clinical-practice-guideline-blood-gas-analysis-and-hemoximetry-2013.pdf).

Final source-hash recheck: every modified/untracked source matches `source-identity.json`.
Schema drift regression, dependency consistency, migration head `m7_0008`, Python
syntax and diff/whitespace checks passed. Changes remain uncommitted on the existing
local demo branch; main is unchanged and no push was performed.
