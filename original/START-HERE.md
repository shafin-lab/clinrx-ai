# RF2 F1–F3 — corrected candidate and preserved evidence

Application **757b163f0f56f1343a32455fc0c4427460dfdd71**, tree **5c1767f0a2aa5ae7ff19459fcdfde2841d3bf166**. Parent is the separate local request-binding correction 84c6482; reviewed RF2 baseline 4429401 remains unchanged. Source and all 17 changed-file snapshots relative to 4429401 are under source/.

Read [REPORT.md](REPORT.md), [source correction boundary](source/files/docs/rf2/F1-F3-CORRECTIONS.md), [runtime read/validation checks](RUNTIME-CHECKS.json) and [data verification](DATA-VERIFICATION.json). The original publication, its 1,173 checksums, raw checkpoints and failed-run attributions are preserved; see ORIGINAL-EVIDENCE-PRESERVATION.json. No old artifact was rewritten.

Local workspace: http://127.0.0.1:5201/ — opt-in, synthetic, loopback only. Clinical execution remains disabled. The candidate is installed locally with the previous frontend/database checkpoints preserved. No browser storage was inspected or cleared.

Exact-candidate CI: https://github.com/shafin-lab/clinrx-ai/actions/runs/39368985675 . **Both jobs passed: 4,350 backend and 749 frontend tests, typecheck and both builds.** See CI-RESULTS.md for final metadata and raw checkout logs. No PR merge or deployment is authorized or performed.

Portable data-only verification: `python verify_evidence.py`. This recomputes source identities, before/after twelve-table preservation and captured request/result correspondences; it does not operate a browser or rerun tests. SHA256SUMS.json covers this package except itself and its derived DATA-VERIFICATION.json output.

RF2-F4 remains the separate nonblocking hydration finding. RF2-12 live desktop/narrow viewport, pointer/keyboard/accessibility and uncoached usability remain unestablished. Do not infer browser acceptance from API/component tests or CI. General durable draft/command recovery remains deferred.
