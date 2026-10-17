# ClinRx Director — packaged-demo browser walkthrough

Evidence-only supplement through PR #23; no ZIP or Mac access required. It does not change application source or replace earlier captured evidence. Production connected execution stays disabled. No merge, deployment, registry push or external hosting.

## Exact application/image relationship

Source: **2539eb61292456706b3c358443a8fdb7a6ece144**

Tree: **d286b5c30bf01bcd0d2f6ab64df0a1d082a27a27**

Image: **sha256:612977c31212cec5adcf9eb6fcd6dc8946808ac3998bd434aaadd4b7e696db0a**, Linux ARM64. Container clinrx-expanded-2539eb6, bound only to **http://127.0.0.1:5183**. [Expected identity](original/expected-image.json), [original live inspect](original/container-inspect.json), [publication-time inspect](supplement/container-inspect.json).

[Packaging source/56-test/ARM64 validation handoff](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6229626772); [complete earlier evidence](https://github.com/shafin-lab/clinrx-ai/blob/2f1e8ea57c9e72fca8928d9a8c6cea89d5ad5fa8/START-HERE.md). Those records establish the earlier build/probe claims; they are not new executions in this walkthrough. Their independent acceptance remains pending and must not be assumed. The original note's “reviewed image” wording identifies the submitted image, not an additional approval.

PR #23 remains draft/open at application head **17e2064c3f1a1761876e9a42c5c7a131646d465c**. Source/evidence review tags do not move its branch or establish exact-head hosted CI.

## What the original walkthrough captured

The same packaged image was restarted locally, without rebuilding/seeding. The packaged page, rather than Vite on 5179, loaded through the same-origin read-only gateway.

- Actual gateway state: **156 items**, **14 of 15** evidence families populated, optional HPI absent, execution_enabled=false. Browser coverage showed five flagged/unknown and two contextual/unplaced records.
- [ABG screenshot](original/abg.jpg): at 09:00, pH7.35, PaCO2 44mmHg, PaO2 88mmHg, each using its own arterial sample context and FiO2 40%. Synthetic sample-time settings remain distinct from current ventilator settings.
- [Echo screenshot](original/echo.jpg): original 08:00 study, RVSP/PASP estimates45mmHg, LVOT VTI17.5cm, EF55%; production tags/source-estimate caveats remain visible. No equivalence, invasive confirmation or current measurement is inferred.
- [Complete original DOM](original/current-dom.txt) preserves source controls, exact times and disabled-execution banner. [Raw API response](original/state-response.json) is a fresh walkthrough-time API capture, not the reused reference snapshot from older frontend reviews.
- [Rows before](original/rows-before-browser.json) and [after](original/rows-after-browser.json) compare equal for all **12 tables**, 162 fact revisions and two retained receipts. They equal the earlier packaged fixture rows. This is retained-state equality, not a fresh browser lookup of both receipts.
- [Runtime log tail](original/container-tail.log) has no captured error. No original persistent console file or original history-result DOM was saved; the history success was observed during the walkthrough and recorded in notes. Do not reconstruct an original network trace from that observation.

Both original screenshots contain JPEG bytes and match their .jpg extensions. Raw production fields, uncertainty and PH report limitations remain unchanged. These source-only display records do not establish clinical interpretation or physiological simultaneity.

## Separately labelled publication-time supplement

To make the history observation inspectable, a new read-only action was captured while preparing this publication. It is not backdated or substituted for the original walkthrough.

- [Fresh exact pH inspector/history DOM](supplement/ph-history-dom.txt), [history screenshot](supplement/ph-history.jpg): fs-PH-60 revision1, source time09:00, pH7.35, its own arterial/FiO2 context, and **one original retained revision at this cutoff**. The UI history control was clicked against the packaged gateway. This is UI capture, not raw packet/request-body evidence.
- [Post-history rows](supplement/rows-after-history.json) remain identical to both original snapshots and the earlier packaged baseline.
- [Browser URL](supplement/browser-url.txt) records port5183; [browser log observation](supplement/browser-logs.json) returned an empty list at this later observation. Do not relabel it as a console capture from the original walkthrough.
- [Capture notes](supplement/capture-notes.json) record scope and restoration of the earlier echo view. Current inspect confirms the same image, running state and loopback-only port.

The local container is intentionally left running at the user's request to view it. This does not revise the earlier packaging-validation cleanup evidence: that earlier test run was stopped, then the user separately authorized this restart/walkthrough. Nothing is exposed externally.

## Direct access and byte integrity

[Original capture checksums](original/SHA256SUMS.json) remain unchanged. [Publication manifest](SHA256SUMS.json) covers original copies, supplements, mirrors and readable exports. No original artifact was renamed or overwritten.

- [Readable 156 API items](readable-state/items-index.json), [state metadata](readable-state/metadata.json).
- [All 12 tables: columns and 170 row files](readable-tables/index.json), preserving raw arrays, named values and parsed payloads.
- [Lossless small text chunks for large raw files](text-mirrors/index.json), with exact lengths, original SHA-256 and ordered chunk hashes. This permits direct reconstruction without ZIP/binary-reader access. Full raw bytes remain beside the mirrors.

Raw state_context is a synthetic bounded read-context value for the local gateway; no signing key, provider/account credential or real patient data is included. The gateway remains loopback-only. Publication does not independently authenticate the context signature; do not infer that claim from checksum success.

[Portable standard-library data-only verifier](verify_evidence.py), [verification output](verification-output.json). It checks published/original hashes, text mirrors, image/loopback correspondence, snapshot equality, all156 stored facts/digests/ingestion/scope, displayed source/time correspondence, source sample/report caveats and exact history labels. These are implementer checks for independent recomputation, not Director acceptance.

## Review requested and limits

Please review whether the captured packaged browser walkthrough supports its narrow claims: 156-record rendering, source-time/sample/echo context, exact inspector/history display, matching packaged image and unchanged tables. Preserve earlier accepted frontend behavior and distinguish this supplement from the separately submitted packaging build/probes.

This is independent-review material captured by the implementer, not a live browser exercise witnessed by Director. It is not a complete timestamped browser/network trace, every-control test, authentication/fresh-visitor certification, all-device/touch/accessibility exercise, hosted CI, external HTTPS/provider validation or clinical validation. No duplicate full test suite was run or claimed for this read-only walkthrough.

Return a bounded verdict with exact identities and remaining evidence gaps, if any. Production connected execution must remain disabled. Do not modify the repository, merge, deploy, host externally or activate gates.
