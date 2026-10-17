# ClinRx Director — d0f94dc local Docker validation only

**New scope: actual Linux ARM64 Docker build, packaged gateway/data, restart and container-browser validation.** The already accepted static-build walkthrough is not being resubmitted. No duplicate code review or test run is requested.

Application **d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982** · tree **384bee3150f0428156549962da1147382f2f03f9**. [Exact source](https://github.com/shafin-lab/clinrx-ai/tree/d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982). Built image/index identity **sha256:ce30c75d0d7ea1ba9cdba43d6c060270449e864a9e30b511f953fb6f17537a78**; local tag clinrx-expanded-demo:d0f94dc-local; container clinrx-expanded-d0f94dc. Browser URL during validation: **http://127.0.0.1:5183/**.

**Production connected execution stays disabled. No merge, deployment, external hosting or gate activation.** This is an evidence-only review tag, not an application branch update. PR #23 remains draft/open/unmerged at 17e2064c3f1a1761876e9a42c5c7a131646d465c. No ZIP or Mac access is required.

## Scope separation — preserve the completed review

- [Previously accepted captured walkthrough](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6229977664), evidence **65eb5810ae6b824cd898be5abd6794caaeebc164**, used the static local build on 5179 and reused earlier API reference data. That verdict stands. Do not reopen it or request duplicate tests solely because this supplement exists.
- [Earlier authored-code validation](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6229921744), evidence **40449e570823e70102741f4290960ae4c95be8de**, remains separate. Its 547-test result is not a Docker test run.
- The older Docker acceptance at 2539eb6 covered the previous image. This new scope asks whether the newly built d0f94dc container actually packages the 156-record fixture and authored explanation while preserving the gated/read-only boundaries.

## 1. Exact source, build and runtime identity

[Original report](original/README.md), [clean-source identity and all 328 source hashes](original/source-identity.json), [raw commit/Git tree identities](source-git-identity.json), [complete clean source files](original/source-context), [source archive bytes](original/source.tar), [exact build command/exit/duration](original/build.json), [raw build log](original/build.log), [image inspection](original/image-inspect.json), [runtime backend hashes](original/runtime-source-sha256.json), [runtime frontend hashes](original/runtime-frontend-sha256.json).

The exact committed archive was used as the build context. Source and tree labels match. Build ran freshly for **linux/arm64**, exit 0, 8.42 seconds, with dependency/base-stage cache reuse; frontend COPY and **VITE_SYNTHETIC_HOSTED=true npm run build** ran including tsc --noEmit. The existing bundle-size warning remains. Runtime backend file hashes match the archive; HTTP-served frontend bytes match the runtime static files. This is captured build/runtime evidence, not Director's own build, a signed supply-chain attestation or distribution of the Docker image itself.

## 2. Real packaged API, exact pins and persistence

[Fresh state response](original/state-response.bin), [post-restart fresh state](original/fresh-state-response.bin), [156 readable item exports](readable-state/items-index.json), [coverage/request context](readable-state/context.json), [complete HTTP metadata transcript](original/http-events.json), [readable response index](readable-http/index.json), [original gateway probe](original/probe.py), [gateway command/result](original/gateway-checks.json), [gateway log](original/gateway-checks.log), [pin checks](original/packaged-authoring-pin-checks.json).

Both states returned **156 items, 14 populated of 15 supported families, optional HPI absent and execution_enabled=false**. All 156 immutable non-HPI authoring pins match the packaged data; fact and assembly digests recompute. Preparation, execution, reconciliation, legacy endpoints, foreign scope and arbitrary files are blocked. Malformed reads fail validation.

The raw state/history request bodies retain ephemeral **synthetic bounded read contexts** deliberately so exact raw-body and restart correspondence can be checked. They are not provider/account/production credentials; no signing key is included. The key was generated only in process memory. The gateway permits only fixed synthetic reads and rejects writes irrespective of a context. Do not claim that hashes authenticate the unseen signing-key signature. No real patient data is included.

[Before rows](original/rows-before.json), [after probes](original/rows-after-probes.json), [after restart](original/rows-after-restart.json), [after all browser checks](original/rows-after-all-browser-checks.json), [never-started packaged SQLite](original/packaged-fixture.sqlite3), [final SQLite](original/final-fixture.sqlite3), [every readable table/row](readable-tables/index.json).

All **12 tables**, 162 fact revisions and two receipts retain identical logical rows throughout the captured checkpoints and match the never-started fixture from the same image. Both captured SQLite files pass integrity_check; their file bytes are **not claimed identical**. These are the original container-validation snapshots/checkpoints, not fresh publication-time replacements.

## 3. Restart, retained receipts and gate closure

[Released response](original/released-response.bin), [released after restart](original/released-after-restart-response.bin), [withheld response](original/withheld-response.bin), [withheld after restart](original/withheld-after-restart-response.bin), [stale-context rejection](original/stale-context-response.bin), [fresh calibration history](original/fresh-history-response.bin), [fresh flowsheet history](original/fresh-flowsheet-history-response.bin).

Same-container/same-image restart preserves both retained response bodies byte-for-byte. Original evidence and all consumed/terminal witness digests correspond to stored rows. Calibration history retains revisions 1/2 and flowsheet history matches its selected fact. The old signed read context fails after restart; a refreshed state restores exact history. This is read-context refresh, not durable command recovery or a new protected-execution lifecycle exercise. No new execution was enabled or dispatched.

## 4. Fresh browser exercise of this container

[Container summary screenshot](original/container-deliverable-summary.jpg), [summary DOM](original/container-deliverable-summary-dom.txt), [bounded browser action record](original/browser-events.json), [captured console errors/warnings](original/browser-errors-warnings.json), [post-browser checks](original/post-browser-results.json).

Fresh page load from 5183 rendered the labelled **Expanded ICU · 156 source records** profile and all four authored panels. The 42 authored controls, 98 summary controls and 13 uncertainty references correspond to container data. Recorded findings/possibilities/confirmation limits remain separate; the generic patient-level relationship stays “not established”. No prepare/execute/reconcile controls are offered.

- **ABG:** [inspector screenshot](original/container-abg-inspector.jpg) and [DOM](original/container-abg-inspector-dom.txt); [real bounded-history result screenshot](original/container-abg-history.jpg) and [DOM](original/container-abg-history-dom.txt). Exact fs-PH-60/1, 09:00 arterial sample, pH 7.35, own 40% FiO2/PEEP 5 context; exactly one retained selected revision.
- **CO:** [screenshot](original/container-co-inspector.jpg), [DOM](original/container-co-inspector-dom.txt). fs-CO-60/1, 4.60 L/min at 09:00, suspect quality and retained method/acquisition limits.
- **Echo:** [keyboard-expanded screenshot](original/container-echo-keyboard-expanded.jpg), [DOM](original/container-echo-keyboard-expanded-dom.txt). m7-RVSP/1, 08:00, source-calculated 45 mmHg; rendered TR/estimated RAP and undocumented RVOT-obstruction caveat. Initial container-echo-expanded.* lacks the expanded text and remains an incomplete capture, not substituted as proof. The subsequent keyboard path was verified and separately captured; pointer/touch certification and a deterministic explanation for the initial capture are not claimed.
- **Infusion:** [screenshot](original/container-infusion-inspector.jpg), [DOM](original/container-infusion-inspector-dom.txt). Exact fs-N-CHANGE/1, 7 mcg/min, concentration 0.08 mg/mL, source-linked 70 kg weight and separately recorded 5.25 mL/h pump support, unresolved raw-unit mappings and no conversion/continuous-delivery/treatment-effect inference.

These are **new captured container observations**, separate from the previously accepted static-build captures. They are implementer observations, not a live session witnessed by Director. The HTTP transcript belongs to explicit gateway probes, not a complete browser network trace; browser-events.json is a bounded action/capture record. Screenshots show recorded viewports, not all panels simultaneously. All JPEG files use matching .jpg extensions.

## 5. Isolation and current-state attribution

[Captured current container inspection](original/current-container-inspect.json), [captured old-container status](original/previous-container-status.json), [runtime user](original/runtime-user.txt), [dependency consistency](original/dependency-check.txt), [Python version](original/python-version.txt), [container logs](original/container-logs.txt), [final checks command/log](original/final-container-checks.json), [post-browser command/log](original/post-browser-checks.json).

Captured configuration: non-root 10001:10001, one worker, capabilities dropped, no-new-privileges, no host mounts, host binding **127.0.0.1:5183 only**. Earlier container/image/data were preserved; earlier container was stopped. These are validation-time captures; publication did not query/restart containers or produce a new live-state claim. A wildcard listener inside Docker is not a wildcard host publication.

## Integrity and review request

[Publication helper notes](PUBLICATION-NOTES.md) disclose a corrected data-only Git-path reconstruction error; it did not affect the original container validation.

[All 432 original artifact checksums](original/SHA256SUMS.json), [publication checksums](SHA256SUMS.json), [lossless text-mirror index](text-mirrors/index.json), [data-only verifier](verify_evidence.py), [implementation verification output](verification-output.json).

Every original artifact is preserved byte-for-byte, including both SQLite snapshots, source archive, raw bodies and incomplete captures. Large/binary artifacts have ordered small base64 chunks with exact sizes/hashes; readable fact/table/HTTP exports are derived from the already captured bytes, not new requests or replacement database exports. No ZIP, Mac access or app execution is required for data-only checks.

**Review the new container scope only:** exact source/tree/build/runtime correspondence; packaged 156-record pins and explanation; actual gateway allow/deny behavior; receipts/context refresh across restart; no-write database checkpoints; captured browser inspectors/expanded echo; loopback/non-root/no-mount isolation. Return a bounded verdict, exact identities, required corrections or evidence gaps, and limitations. Preserve prior completed verdicts. No duplicate suite/review is requested solely for publication.

No application code changed, no test suite or container rebuild ran for this publication, and no new independent execution is implied. The fresh image build/typecheck, HTTP probes and browser checks above belong to the existing local validation. No AMD64 build, hosted CI, external HTTPS/access-control verification, hosting-provider approval, clinical validation or production execution activation is claimed. Keep production execution disabled. Do not modify, merge, deploy, host externally or activate gates.
