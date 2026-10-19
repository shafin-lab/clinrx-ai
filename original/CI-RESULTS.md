# Exact-candidate CI — SUCCESS

[Run 39306712460, attempt 1](https://github.com/shafin-lab/clinrx-ai/actions/runs/39306712460) completed successfully.

Both raw job logs identify exact checkout **44294015e5439f581c8107bb7a0f72a77f328406**, workflow_dispatch at refs/tags/clinrx-rf2-4429401. The tree is eb1d921cba282bc8cce208f1282c0cd9e0a969e4. This was not PR #23’s old source head or a merge checkout.

- Backend: **4338 passed**, one existing Starlette/httpx warning, 1083.08 seconds. Python 3.11.6; schema head m7_0008; pinned dependency consistency passed.
- Frontend: **739 passed / 25 files**. Node 22.13.0/npm 10.9.2; typecheck, default build and explicit synthetic RF1/RF2 authoring build passed.
- Existing bundle-size warning remains nonblocking. The Actions Node20 deprecation annotation concerns action runtime; it is distinct from setup-node’s recorded Node22 application environment.

Raw logs: ci/final-hosted.log. Final metadata: ci/final-metadata.json. The older in-progress metadata is preserved with its original name, not represented as final. These are implementation-retrieved hosted results, not an independent Director rerun.

Earlier review-tag runs 39304996736 and 39305467775 were cancelled when narrow final admission/ownership corrections were added. They are not final-candidate acceptance evidence. No assertion, test timeout or twenty-minute backend job timeout was relaxed.

Only review tags were published for CI. PR #23’s application branch remains unchanged; no merge or deployment occurred. CI establishes automated results for this exact candidate, not live browser usability, container or clinical acceptance.
