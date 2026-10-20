# RF2 F1–F3 — focused Director re-review

Application **757b163f0f56f1343a32455fc0c4427460dfdd71**; tree **5c1767f0a2aa5ae7ff19459fcdfde2841d3bf166**. Reviewed baseline **44294015e5439f581c8107bb7a0f72a77f328406**. Approved specification a4547e215a8c4c20bd04e807d0287c5e1d575c39.

1. Read [original package guide](original/START-HERE.md), [correction report](original/REPORT.md), [correction boundaries](original/source/files/docs/rf2/F1-F3-CORRECTIONS.md) and [exact-head CI](original/CI-RESULTS.md).
2. Inspect [17-file manifest](original/source/FILES.json), [source diff](original/source/changes.diff), [raw commit](original/source/commit.raw), targeted regressions and preserved negative controls in original/logs/.
3. Inspect [runtime checks](original/RUNTIME-CHECKS.json), [data-only verification](original/DATA-VERIFICATION.json), raw redacted HTTP events, before/after SQLite bytes and twelve-table row exports. Eleven read/validate operations leave 182 fact revisions and two receipts unchanged. They are not a new browser save/reload exercise.
4. [MIRRORS.json](MIRRORS.json) provides lossless readable parts for large text and binary files. Concatenate UTF-8 parts directly; concatenate/decode base64 parts. Original artifacts remain unchanged. PUBLICATION-SHA256SUMS.json covers every published file except itself. No ZIP or Mac access is needed.
5. [Prior RF2 evidence](https://github.com/shafin-lab/clinrx-ai/tree/1c776ede26347bfb791c59e958d680a7fb380226) is preserved, with all 1,173 checksums rechecked. It retains its original attribution and findings.

## Review boundaries

F1: outer repository and all history pins must agree. F2: new cross-owner amendments are rejected; RF2-owned corrections preserve availability and unedited context; retained exact lookup/retry remains compatible. F3: explicit current-source review and historical retention acknowledgement, final transaction-bound recheck, exact command-bound rejection and unchanged uncertain-save recovery. No automatic replacement, successor substitution or retry.

The separate native-fetch receiver correction 84c6482 is included in the candidate ancestry. Its regression models the receiver issue; it is not a captured live-browser exception.

Final local results: 32 focused backend, 39 focused frontend, 749 full frontend, typecheck and both builds. Earlier 57-backend and 746-frontend results precede final refinements; initial failures remain disclosed. Exact-candidate hosted CI: **4,350 backend / 749 frontend**, typecheck, default and explicit RF1/RF2-authoring builds passed: [run 39368985675](https://github.com/shafin-lab/clinrx-ai/actions/runs/39368985675). Both checkout logs identify this exact source, not PR #23's older head or merge checkout.

RF2-F4 remains open and nonblocking. RF2-12 live browser, narrow-viewport/accessibility and uncoached usability are not established. Browser access was blocked by tool policy; no alternate browser workaround was used. API checks, served asset equality and component tests do not establish browser acceptance. General durable draft/command recovery remains deferred.

This public package contains synthetic evidence only. No credentials, signing keys, browser storage or user screenshots are included. Preserve prior RF1/hemodynamics acceptances. No duplicate full suite is requested solely for publication. Director re-review remains pending. Execution remains disabled; no merge, deployment, external hosting or gate activation.
