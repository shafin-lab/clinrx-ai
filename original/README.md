# Expanded synthetic ICU authored explanation — local validation

Source `d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982`; tree `384bee3150f0428156549962da1147382f2f03f9`. Parent: `2539eb61292456706b3c358443a8fdb7a6ece144`. Local branch feature/comprehensive-synthetic-demo; clean after commit. No push, merge, deployment, external hosting or gate activation.

The new fixed authored profile requires all 156 non-HPI records, exact full references/content/digests, placement, contextual links, disclosures and patient/window correspondence. It adds four panels: ABG sequence; flow adequacy unresolved; earlier echo; and infusions/perfusion. Recorded assertions, unconfirmed possibilities and barriers to confirmation remain separate. Clinical background links are retained; this text is not clinically validated or Director accepted. All earlier reviewed evidence remains untouched.

The original 41-record profile remains separately supported and explicitly labelled. Replacing the entire dataset with that exact original case selects its original text; this is not reuse of the expanded explanation. Optional HPI is unconsumed but foreign patient/encounter HPI still withholds. Regression cases combine the legitimate decoded HPI collision fixture with the expanded fixture in both orders; these are unit-constructed combinations, not newly exported API fixtures.

## Checks

- `npm test -- --maxWorkers=2`: **547 passed across 14 files**, exit 0, 34.41 seconds.
- `npm run build`: typecheck and default build passed, exit 0.
- `VITE_SYNTHETIC_HOSTED=true npm run build`: passed locally, exit 0; no deployment.
- `VITE_API_BASE_URL=http://127.0.0.1:8766 npm run build -- --outDir /tmp/clinrx-authored-checks/local-preview`: passed, exit 0.
- `git diff --check`: passed, exit 0.
- Node 22.13.0; npm 10.9.2. Source hashes are in tested-source-sha256.json. These runs preceded the commit; committed source bytes are unchanged. Existing bundle-size warning remains.
- Data-only recomputation: all 156 fresh API fact digests, assembly digest and full expanded profile pins match. Execution is false. All 12 original and isolated-copy database tables have identical rows and SQLite integrity passes. This is logical-row correspondence, not SQLite file-byte equality or a complete historical network trace.

## Browser observations

Stable local build at http://127.0.0.1:5179/ using loopback API 8766. The expanded authored profile appears in Patient summary. Exact source clicks inspected fs-PH-60/1: arterial pH 7.35 at 09:00, own specimen fs-arterial-sample-60 and FiO₂ 40%; fs-CO-60/1: 4.60 L/min at 09:00, suspect quality, SwanGanz/HemoSphere; m7-RVSP/1: 45.0 mmHg at 08:00, source-calculated tag and estimate caveats. These are implementation-observed browser checks, not independent Director execution. Summary contains 42 authored source controls. Source/uncertainty display and existing patient-level relationship-not-established remain visible. No complete network trace is claimed.

The initial Vite walkthrough repeatedly reloaded after websocket reconnects; its first screenshot/DOM are retained as incomplete attempts, not substituted for the stable capture. Stopping that Vite process also caused the earlier launcher's API to shut down. A loopback-only static build replaced Vite on 5179, and a new API process on 8766 uses a SQLite backup of the unchanged original demo database with a new ephemeral in-memory signing key. run_local_api.py contains no signing-key value. The accepted Docker image/container at 5183 was not rebuilt or modified. This new explanation has no new container acceptance. Local state loading/inspector use is shown; no protected execution was attempted.

## Disclosed initial failures

An initial sandbox-restricted focused run could not write Vite temporary configuration (EPERM) and was rerun with authorized repository write access. The first executable focused run had 71 passes and two assertion failures: an old test expected the expanded authored explanation to stay unavailable; a new test used RVSP rather than the existing Estimated RVSP accessible name. Those assertions were corrected to cover the newly authorized profile and actual source label. focused-initial.log is retained. The complete final suite then passed. Prior parallel-run timeout uncertainty is not attributed to a proven cause here.

## Boundaries

No backend, schema, fixture, dependency, migration, clinical policy or production execution configuration changed. A stale hosting checklist now distinguishes packaged 156-record content from the explicit 41-record default. No backend suite, hosted CI, new container check, external usability certification or clinical validation is claimed for this increment. PR #23 remains unchanged. Evidence remains local until publication is requested. Screenshot extensions match detected JPEG bytes. Existing reviewed originals are preserved.
