# Exact-candidate CI — SUCCESS

[Run 39368985675, attempt 1](https://github.com/shafin-lab/clinrx-ai/actions/runs/39368985675) completed successfully.

Both job checkout logs identify **757b163f0f56f1343a32455fc0c4427460dfdd71**, tree **5c1767f0a2aa5ae7ff19459fcdfde2841d3bf166**, via workflow_dispatch on refs/tags/clinrx-rf2-f123-757b163. This is not PR #23's old head or a merge checkout.

- Backend: **4,350 passed**, one existing Starlette/httpx warning, 1027.82 seconds. Python 3.11.6; migration head m7_0008 and pinned dependency consistency passed.
- Frontend: **749 passed / 27 files**. Node 22.13.0/npm 10.9.2; typecheck, default and explicit RF1/RF2 authoring builds passed. Existing bundle warning remains.

Final raw log: logs/hosted-final.log; metadata: ci-final.json. Older in-progress metadata and implementation failures retain their original attribution. The Actions Node20 deprecation annotation refers to pinned action runtimes being forced to Node24, distinct from the recorded Node22 application runtime. No workflow, timeout or assertion threshold was changed.

PR #23 remains draft/open at unchanged 17e2064c3f1a1761876e9a42c5c7a131646d465c. Only an immutable source review tag was published for CI. No merge or deployment occurred. CI is automated execution evidence, not independent Director, browser, container or clinical acceptance.
