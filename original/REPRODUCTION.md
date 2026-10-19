# Reproduce bounded checks

Use the isolated source at 44294015e5439f581c8107bb7a0f72a77f328406 and existing pinned dependencies. Do not use real patient data. The captured logs remain the evidence for the actual runs; the commands below are reproduction instructions, not a new execution record.

From the repository root, with its Python 3.11.6 environment and backend on PYTHONPATH:

```sh
PYTHONPATH=backend python -m pytest tests/test_renal_fluid_entry.py tests/test_synthetic_authoring.py tests/test_guided_authoring.py -q
PYTHONPATH=backend python docs/rf2/carrier_probe.py
```

From frontend:

```sh
npm ci
npm test -- --maxWorkers=2
npm run build
VITE_SYNTHETIC_HOSTED=true VITE_SYNTHETIC_AUTHORING=true VITE_SYNTHETIC_RF1=true VITE_SYNTHETIC_RF2=true npm run build
```

The existing workflow runs the complete backend suite in a clean pinned environment and records the actual checkout. See CI-RESULTS.md. No repeat full suite is required solely to read this evidence.

The source README documents the isolated local gateway. It never seeds or resets on startup. Use an absolute path to a disposable synthetic database copy; bind only to 127.0.0.1. Keep the accepted original database separate. The saved real-API journey runner is not read-only: it intentionally creates seven ledgered synthetic revisions/records and must not be run twice against the retained evidence checkpoints. Inspect its code first and use a fresh copy for any new exercise.

The data-only verifier is safe against retained checkpoints:

```sh
python verify_evidence.py
```

Supplemental handover checks are outside frozen source. To reproduce them, temporarily copy supplement-tests.tsx into frontend/tests/rf2.supplement.test.tsx and run that one file with the same test runner. Remove the copy afterward; these four cases are not part of exact-candidate CI's 739-test total.

Browser access was denied by the tool security policy. The operator did not use alternate browser surfaces, headless automation or an indirect proxy. A separately permitted live browser session is needed for RF2-12 before claiming complete interface/usability acceptance.
