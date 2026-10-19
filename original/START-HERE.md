# RF2 — combined local milestone validation

Candidate **44294015e5439f581c8107bb7a0f72a77f328406**, tree **eb1d921cba282bc8cce208f1282c0cd9e0a969e4**.
Approved specification a4547e215a8c4c20bd04e807d0287c5e1d575c39; application baseline 5cb73212ae6104b02bad361886cd9507795d88bf.

**Exact-candidate CI passed: 4338 backend and 739 frontend tests, typecheck and both build modes.** See [CI-RESULTS.md](CI-RESULTS.md).

Start with [MILESTONE-REPORT.md](MILESTONE-REPORT.md), then [ACCEPTANCE-MATRIX.md](ACCEPTANCE-MATRIX.md). Source identities, exact diff and all 22 changed files are under `source/`. Ownership mapping and carrier proof are in `source/files/docs/rf2/`.

The local workspace is http://127.0.0.1:5201/ — choose **Renal charting and handover**. The accepted RF1 workspace and original database were preserved. This is a disposable synthetic authoring workspace. Clinical execution is unavailable. No merge, deployment or external hosting occurred.

`api-journey/` contains raw requests, redacted responses, timestamped events and before/after SQLite checkpoints. Its positive journey used the initial implementation checkpoint 11ddd8a; final supplements under `final-revalidation/` and `ownership-revalidation/` retain their own source attribution. The latter confirms final candidate ownership guards, exact retained recovery and unchanged rows. `tested-build/` contains exact served frontend bytes, identical across those source checkpoints.

`logs/` preserves intermediate failures alongside final passing runs; filenames are not interchangeable source attribution. Read the report before interpreting results. Supplemental handover tests are provided separately in `supplement-tests.tsx`; they are not part of the frozen source's 739-test total.

Run `python verify_evidence.py` for data-only checksum, SQLite, original-row preservation, fact/digest/ingestion and exact-command correspondence checks. This does not operate the application or establish live browser behavior. The combined manifest excludes mutable `runtime/` files and itself.

**Remaining acceptance gap:** browser access was denied by the available tool's security policy; no alternate surface was used. Desktop/narrow viewport, keyboard/pointer, accessibility and uncoached end-to-end usability are not demonstrated. General durable draft/command recovery remains deferred. Independent Director acceptance of RF2 is outstanding.
