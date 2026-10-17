# Expanded authored patient explanation — local Docker validation

Completed 17 October 2026 (Asia/Kolkata). **PASS for the exercised local Linux ARM64 container scope**, implementation-produced evidence; independent Director review remains separate.

Application **d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982**; tree **384bee3150f0428156549962da1147382f2f03f9**. Built from a clean Git archive, with 328 tracked source files hashed in source-identity.json. The repository is clean, and no application files were changed, committed or pushed for this validation. No merge, deployment, external hosting or production gate activation occurred.

## Current local demo

- URL: **http://127.0.0.1:5183/**; Patient summary is left open.
- Image tag: **clinrx-expanded-demo:d0f94dc-local**.
- Image/index identity reported by Docker: **sha256:ce30c75d0d7ea1ba9cdba43d6c060270449e864a9e30b511f953fb6f17537a78**; actual platform **linux/arm64**.
- Container: **clinrx-expanded-d0f94dc**, running as 10001:10001, one worker, no host mounts, all capabilities dropped, no-new-privileges, host binding **127.0.0.1:5183 → 8080** only.
- Earlier accepted container **clinrx-expanded-2539eb6** is preserved and stopped; its image and data have not been replaced. Original static local build/API on 5179/8766 were not changed. The new Docker image uses its packaged fixture and its own gateway.

## Story and flow verification

A visitor opens the packaged frontend, selects Patient summary, and receives the bounded 156-record synthetic state through the same-origin read-only gateway. The exact non-HPI state matches all 156 authoring pins, so the separately labelled expanded authored explanation appears. Source clicks preserve selected fact identity and context; bounded history reads the real container API. Recorded assertions, unconfirmed possibilities and confirmation barriers remain separate.

| Boundary | Result | Evidence |
|---|---|---|
| Exact source → image | PASS | Clean archive, source/tree labels, build.log, runtime-source-sha256.json and image-inspect.json |
| Image frontend build | PASS | Container build performs npm ci and hosted-mode npm run build, including tsc --noEmit; build 8.42s, exit 0 |
| Gateway → packaged state | PASS | Fresh state HTTP bodies: 156 records, 14 populated families, optional HPI absent, execution_enabled=false |
| Data → explanation | PASS | packaged-authoring-pin-checks.json: 156 complete exact pins; assembly and fact digests recomputed |
| Explanation → exact sources | PASS | Captured 42 authored controls, 98 summary controls, 13 uncertainty controls; actual four inspector visits and pH history |
| Denied writes / recovery | PASS | Preparation, execution, reconciliation and legacy routes rejected; retained receipts unchanged after same-container restart |
| Browser/API → unchanged data | PASS | All 12 tables equal before/after HTTP probes, restart and browser use; never-started packaged fixture and final snapshot have identical logical rows |

## Browser observations and actual captures

Fresh page loaded from **5183**, after the new container had restarted. This is the packaged demo, not the earlier static build on 5179. browser-events.json records captured states and selected actions; it is a bounded implementation action record, not a complete browser network trace.

- container-patient-summary / container-deliverable-summary: explicit **Expanded ICU · 156 source records · synthetic-expanded-icu-interpretation/1**, four authored panels and unconfirmed combined possibility. Patient-level relationship stays “not established”. No preparation/execution/reconciliation button is offered. All source-control identities, times and numeric/qualitative values match the container's fresh API reference.
- container-abg-inspector: fs-PH-60/1, arterial pH 7.35 at 09:00, specimen fs-arterial-sample-60, its own FiO2 40% and PEEP 5 cmH2O. container-abg-history demonstrates the actual bounded-history call returning exactly revision 1 at the cutoff.
- container-co-inspector: fs-CO-60/1, 4.60 L/min at 09:00, **suspect** quality, SwanGanz/HemoSphere and retained acquisition/unknown calibration context.
- container-echo-keyboard-expanded: m7-RVSP/1 at 08:00, source-calculated estimate 45.0 mmHg; the open estimate-basis disclosure visibly retains TR/estimated RAP support and undocumented RVOT-obstruction caveat. No PH/PAH diagnosis is inferred.
- container-infusion-inspector: fs-N-CHANGE/1, 7 mcg/min, concentration 0.08 mg/mL; exact 70 kg weight and separately recorded 5.25 mL/h pump support; unresolved raw-unit mapping, with no dose conversion, continuous exposure or treatment effect asserted.
- browser-errors-warnings.json contains zero captured error/warning entries.

**Initial disclosure capture limitation:** container-echo-expanded.* was saved after the first pointer action and does not contain the expanded caveat text. It is retained as an incomplete attempt, not relabelled as expanded proof. Keyboard activation was then verified with details.open=true and rendered text, and separately saved as container-echo-keyboard-expanded.*. This validates the recorded keyboard path; it does not certify all pointer/touch interactions or establish a deterministic application defect from that initial capture.

Every new screenshot uses an extension selected from actual PNG/JPEG magic bytes. Screenshots show individual recorded viewports, not every panel simultaneously. Complete DOM captures are included. No complete browser request/response trace or independent live review is claimed.

## Gateway, persistence and runtime checks

probe.py ran against the real container (gateway-checks.json/log; exit 0, 12.54s). It checked state/content digests and all 156 pins, index/assets/health, exact CAL/2 history containing revisions 1/2 and fs-D-CHANGE history, retained released/withheld receipts and original/terminal witnesses, rejected write routes/foreign scope/arbitrary files/malformed reads, all-table no-write comparisons and non-root/loopback/no-host-mount constraints. The same container/image restarted: retained receipt response bytes were identical, the old signed context was rejected, fresh state restored exact history, and rows remained unchanged.

final-check.py passed (exit 0): both SQLite snapshots have integrity_check=ok; all 12 tables match the never-started fixture, with 162 fact revisions/two retained receipts. SQLite backup files are not claimed byte-identical to one another. All runtime backend Python hashes match the clean archive, and the image source label/platform match the requested identity.

post-browser-checks.py passed (exit 0): all 12 tables remain unchanged after every browser visit, runtime frontend hashes match HTTP-served asset/index bytes, captured controls/inspectors correspond, and the new container remains running with the earlier container preserved/stopped.

No source change required a duplicate host test suite. The previous **547 frontend tests** belong to the earlier d0f94dc validation and are not claimed as rerun inside Docker. Typecheck/hosted build did run freshly inside this image. No new full backend suite, AMD64 build, hosted CI, external HTTPS/access protection, clinical validation or hosting-provider acceptance is claimed. The existing bundle-size warning remains nonblocking.

## Evidence and boundaries

Exact commands, cwd, durations and exits are in build/run/gateway-checks/final-container-checks/post-browser-checks JSON/log pairs. Source archive/context/hash manifest, image/container inspection, raw HTTP bodies and header metadata, all-table exports, two SQLite snapshots, screenshots/DOM and browser action records remain local in this directory. HTTP context signatures are ephemeral local read contexts, not production credentials; any later publication needs an explicit retention/redaction strategy. Signing keys are generated in process memory and are not included.

Production connected execution stays disabled. This is a synthetic container exercise, not clinical validation or permission to host. No merge, deployment, registry push, application-branch update or external hosting occurred. Independent review of this new container evidence is pending.
