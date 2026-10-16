# ClinRx PR #23 — isolated browser-to-real-API validation

**Result: PASS for the exercised isolated synthetic lifecycle. Submitted evidence, not an independent Director acceptance verdict or clinical validation.**

Source: `17e2064c3f1a1761876e9a42c5c7a131646d465c`  
Tree: `3723885d26a9ba62ff271361a1c8a6a7351de63c`  
Source/working tree unchanged before and after. No commit, push, merge, deployment or production gate activation in this validation. Both disposable servers were stopped at completion; retained databases and artifacts remain local for review.

## Boundary and environment

Actual reviewed React app served by Vite on `127.0.0.1:5178`, calling the actual reviewed FastAPI app under Uvicorn on `127.0.0.1:8765`. This was a browser exercise through HTTP, not TestClient or mocked frontend responses. Python 3.11.6, Node 24.12.0, npm 11.6.2, local macOS and Codex in-app browser. Historical simulation instant `2026-10-08T12:01:00+00:00`; review window `08:00–10:00 UTC` on that day. Each scenario used a separate freshly bootstrapped SQLite database with migration `m7_0008`, independent signing key and repository identity. Existing service on port 8000 was untouched.

Only an external disposable harness enabled `APIConfig(environment='test', circulatory_execution_enabled=True)` for these test-owned databases. Source configuration and environment loader remain unchanged and gated. Gate-closure checks changed only this test-owned app configuration. Production was not contacted or changed.

Seed: the checked-in all-15-family, 21-record synthetic fixture, plus a pressure revision 2 asserting applied cuff calibration with exact `m7-CAL/1` adequacy provenance. Browsed bounded state contains the current 21 records. Every browser preparation explicitly selected `m7-P/2`, `m7-L/1`, `m7-V/1` and `m7-CAL/1`; four exact inference inputs were verified against captured state and persisted originals.

## Results

| Scenario | Browser / API / storage result | Execution UUID |
| --- | --- | --- |
| release | Released; browser retained lookup returned identical receipt | `0680dad6-f324-4802-9a52-ecebb6205934` |
| same_value | Support-only same-value successor withheld; original CAL/1 retained, terminal CAL/2 | `48714dc1-8166-4dfe-b11e-fdf39b8a91ad` |
| provenance | Provenance-only successor withheld; original CAL/1 retained, terminal CAL/2 | `2de048b9-49d2-4c8e-8d7f-70090e18918b` |
| withdrawn | Withdrawn successor withheld; original CAL/1 retained, terminal withdrawn CAL/2 | `0c112307-c744-48d0-add8-579027683ec6` |
| pressure | Primary pressure successor withheld; original P/2 retained, terminal P/3 | `27ddecd3-5f4e-4096-a0b2-65b73437f8b1` |
| malformed | Committed receipt with schema-valid foreign inference reference delivered to browser; completion unknown; explicit reconciliation recovered original receipt | `585c11db-0222-48ad-a10f-34b969084b7e` |
| post_commit | Real API committed, then harness delivered HTTP 500; completion unknown; explicit reconciliation recovered receipt | `e24eeea3-1e3c-4555-9c2f-5b4c045e1722` |
| timeout | Real API committed; delivery delayed 35 seconds past actual 30-second client deadline; timeout then explicit reconciliation recovered receipt | `b1fa6248-a5db-4ca2-b668-05e083bbc897` |
| absent | First request intercepted before API dispatch, delivered 502; reconciliation absent; no receipt/no automatic retry; explicit same-command retry then released | `15109137-34c2-4cf4-89aa-afd3bc4557ef` |
| gate_pending | Prepared while isolated gate open; gate then closed; execution 422 and reconciliation absent; zero execution receipts | `9ddde64b-f5cf-46e0-bcef-91181158dc2d` |

## Gate and recovery evidence

With the isolated gate closed, browser pressure selection and preparation were disabled. Real direct HTTP preparation was also rejected with 422 and did not append facts or receipts. Existing release's matching retry returned byte-identical HTTP response body; reconciliation returned committed_match. Browser retained lookup worked with the gate closed for the original release, withheld support correction, and all three committed fault-response cases.

For malformed, post-commit error and timeout cases there was exactly one preparation and one execution request: reconciliation was lookup-only. All captured execution and reconciliation request bodies carried the exact original command. For the absent case, the zero-receipt/one-attempt checkpoint was captured before the explicit browser retry; both execution attempts used identical command bytes. No replacement UUID or automatic execution was observed.

Fault injection occurred outside the real API after it returned, except the explicitly pre-dispatch absent scenario. The HTTP 500 is a simulated delivery failure after a real commit, not a claim to have reproduced an internal production projection failure. The timeout is real client deadline behavior with delayed delivery, not a socket-level packet-loss test. Raw original and modified response bodies are retained separately. No fault fabricated a successful backend receipt.

## Evidence verification

`verify_evidence.py` passed against every captured lifecycle: persisted receipt digest matches stored payload; captured successful response record equals that payload; selected original facts equal both captured bounded state and current original revision rows; exact support/terminal identities, withholding outcomes, original command correspondence, receipt counts and recovery responses match. The gate probe independently compared all fact/receipt rows before and after closed-gate rejection/recovery and found them unchanged. These scripts inspect the recorded evidence; they do not replace the browser exercise.

Browser snapshots and screenshots include prepared/completed states, each correction result, each uncertain completion, absence before explicit retry, and closed-gate lookup. Browser diagnostic captures report no console warnings/errors for the captured tabs. Network evidence is a harness HTTP transcript with request/response body files and Origin metadata, not a browser HAR export.

An initial same-value attempt entered preparation_unknown with a transport error and no corresponding completed POST exchange captured. It was not retried by that page. Its screenshot/DOM remain separately labelled. A direct API diagnostic created one additional unexecuted preparation; a fresh browser then completed the acceptance scenario. Two browser-control interruptions (a label-selection timeout and reload not resetting a completed page) were resolved using the visible dropdown and the explicit Start another selection control. They are not reported as newly reproduced code defects. The interrupted attempt and diagnostic preparation are excluded from acceptance counts; they remain in raw evidence.

**Reload/closure can still lose in-memory commands. Durable browser-session recovery is deferred and was not implemented or claimed.** Independent Director review remains required before granting connected lifecycle acceptance; production execution remains disabled.

## Reproduction and artifacts

Run from an exact clean checkout, copying this harness into a new empty output directory (do not reuse existing databases). With `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=backend:<output-directory>`, run `backend/venv/bin/python -m uvicorn harness:application --host 127.0.0.1 --port 8765`. In frontend, run `VITE_API_BASE_URL=http://127.0.0.1:8765 npm run dev -- --host 127.0.0.1 --port 5178 --strictPort`.

Set `control.json` to the scenario name and optional fault before loading state. Use the actual page's Load circulatory evidence, exact primary dropdowns, explicit CAL/1 support checkbox, Prepare, Execute, Reconcile, Start another selection and retained lookup controls. Faults are `malformed`, `post_commit_error`, `timeout`, `absent`; correction scenarios are keyed by their scenario names. Set `closed:true` only in this disposable control file for gate checks. Run gate_probe.py while the servers run, then verify_evidence.py against captured artifacts. Stop only these two test servers.

All raw body files, ten databases, screenshots, DOM snapshots, console captures, server logs and reproduction/verification scripts are retained beside this report. `checksums.json` identifies every retained file. No new full regression run was needed because application source did not change; prior exact-tree 4,221 backend / 423 frontend hosted-CI evidence remains separate from this browser exercise.


<details>
<summary>Machine-checked receipt identities and results</summary>

```json
{
  "source_head": "17e2064c3f1a1761876e9a42c5c7a131646d465c",
  "source_tree": "3723885d26a9ba62ff271361a1c8a6a7351de63c",
  "working_tree_clean": true,
  "cases": [
    {
      "scenario": "release",
      "status": "PASS",
      "execution_id": "0680dad6-f324-4802-9a52-ecebb6205934",
      "outcome": "released",
      "receipt_count": 1,
      "execution_attempts": 2,
      "payload_sha256": "9a1081353e750de866b4ed799806fb09944942c903324543e20c81cf7fac2d0c",
      "original_support_retained": true,
      "terminal_support_revision": "1"
    },
    {
      "scenario": "same_value",
      "status": "PASS",
      "execution_id": "48714dc1-8166-4dfe-b11e-fdf39b8a91ad",
      "outcome": "withheld",
      "receipt_count": 1,
      "execution_attempts": 1,
      "payload_sha256": "ee1d11d688d63536bcc4958337ede6ee8d074aef4165e83349ca27de031c4ff9",
      "original_support_retained": true,
      "terminal_support_revision": "2"
    },
    {
      "scenario": "provenance",
      "status": "PASS",
      "execution_id": "2de048b9-49d2-4c8e-8d7f-70090e18918b",
      "outcome": "withheld",
      "receipt_count": 1,
      "execution_attempts": 1,
      "payload_sha256": "26ef880d6270a5eb7c3a14a4e3570b7ec31c1d30ff743d0dcc0eb6eaa78d422b",
      "original_support_retained": true,
      "terminal_support_revision": "2"
    },
    {
      "scenario": "withdrawn",
      "status": "PASS",
      "execution_id": "0c112307-c744-48d0-add8-579027683ec6",
      "outcome": "withheld",
      "receipt_count": 1,
      "execution_attempts": 1,
      "payload_sha256": "0c43ea25827cf583454c09e0b210d94873cff1ca42afea056df21d27b8588b06",
      "original_support_retained": true,
      "terminal_support_revision": "2"
    },
    {
      "scenario": "pressure",
      "status": "PASS",
      "execution_id": "27ddecd3-5f4e-4096-a0b2-65b73437f8b1",
      "outcome": "withheld",
      "receipt_count": 1,
      "execution_attempts": 1,
      "payload_sha256": "6e40e6d2cce23c15171ef82c1997590fd7307ea2ec343a5158eb2cf648f39ae3",
      "original_support_retained": true,
      "terminal_support_revision": "1"
    },
    {
      "scenario": "malformed",
      "status": "PASS",
      "execution_id": "585c11db-0222-48ad-a10f-34b969084b7e",
      "outcome": "released",
      "receipt_count": 1,
      "execution_attempts": 1,
      "payload_sha256": "c085bf4be272c6265fa631e3813137ddadf3c8a35f4ed8cd05cdfcbb34761880",
      "original_support_retained": true,
      "terminal_support_revision": "1"
    },
    {
      "scenario": "post_commit",
      "status": "PASS",
      "execution_id": "e24eeea3-1e3c-4555-9c2f-5b4c045e1722",
      "outcome": "released",
      "receipt_count": 1,
      "execution_attempts": 1,
      "payload_sha256": "9eece494cddffcbc04292c680e7a51b050ca9257b87f45a376104a0f4db08873",
      "original_support_retained": true,
      "terminal_support_revision": "1"
    },
    {
      "scenario": "timeout",
      "status": "PASS",
      "execution_id": "b1fa6248-a5db-4ca2-b668-05e083bbc897",
      "outcome": "released",
      "receipt_count": 1,
      "execution_attempts": 1,
      "payload_sha256": "c41fe826b016d3e61f4797abd2370ff5a3b62c51a940a53275df6d5f20002632",
      "original_support_retained": true,
      "terminal_support_revision": "1"
    },
    {
      "scenario": "absent",
      "status": "PASS",
      "execution_id": "15109137-34c2-4cf4-89aa-afd3bc4557ef",
      "outcome": "released",
      "receipt_count": 1,
      "execution_attempts": 2,
      "payload_sha256": "45079f2bdfad87b03bc1f20345bf52c67c18bcc0ee7d3b76863d3cd0abf861c3",
      "original_support_retained": true,
      "terminal_support_revision": "1"
    },
    {
      "scenario": "gate_pending",
      "status": "PASS",
      "execution_id": "9ddde64b-f5cf-46e0-bcef-91181158dc2d",
      "receipt_count": 0,
      "execution_http_status": 422
    }
  ]
}
```
</details>

<details>
<summary>Gate-closed storage proof</summary>

```json
{
  "gate": false,
  "preparation_status": 422,
  "retained_retry_status": 200,
  "retained_retry_bytes_identical": true,
  "reconciliation_status": "committed_match",
  "storage_before": {
    "fact_revision": "3fe495fe5b79015ca410cf880b0e69dcfae4bb6525a0217950ba1c789df98dde",
    "circulatory_execution": "54a302df9295dcb6f644739b5a00e8bff026220097883fa641504563903abe09"
  },
  "storage_after": {
    "fact_revision": "3fe495fe5b79015ca410cf880b0e69dcfae4bb6525a0217950ba1c789df98dde",
    "circulatory_execution": "54a302df9295dcb6f644739b5a00e8bff026220097883fa641504563903abe09"
  },
  "blocked_pending_receipts": 0
}
```
</details>

<details>
<summary>HTTP transcript (API status before any delivery fault)</summary>

```json
[{"number":1,"scenario":"release","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"505ee4a5669936392d829b11f1934f0700745ed00eadd3a76f8a38860f5e7679"},{"number":3,"scenario":"release","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"cbd341cf421a229a7e6d1a9a930449e50ced213d08c947aa88507db4c131a89e"},{"number":5,"scenario":"release","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"597d1fcb242af9061f618a055f9f3166fefe7232f80ef94c733ca7216c3e7423"},{"number":6,"scenario":"release","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews/0680dad6-f324-4802-9a52-ecebb6205934","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"597d1fcb242af9061f618a055f9f3166fefe7232f80ef94c733ca7216c3e7423"},{"number":7,"scenario":"same_value","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"c3752e943336f34d439e7a6a686c8038acf461640f488784e83865f26c3d42cb"},{"number":9,"scenario":"same_value","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"0c099aa5b6a15b1aaf8b67ea9fa0252459078257117bbc3399a94f0ce1a313af"},{"number":11,"scenario":"same_value","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"8c58e41c9892ac40ecf87183e86fa3c4b31315dc78c55ebf11f7aa104059d227"},{"number":13,"scenario":"same_value","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"1ec58d73591ce3d812431b36bf4c4b2d46ecef6179a1dc3f439652b103b1efa2"},{"number":15,"scenario":"same_value","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"20ed171e65d748f379c05348517d66dfa2702753fbbef158906e45d08fa4e4ec"},{"number":16,"scenario":"provenance","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"a6f0e5b99ca4e4cbabf7727494056c01c75eb5255fd892ac0f0c2b1dbb8869b3"},{"number":18,"scenario":"provenance","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"bcff5ab8fd836836bf9ed04a65021f47b2a3a346192a5e75a2b3957e2cd5277f"},{"number":20,"scenario":"provenance","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"5043fb946ce858c6a469d574415adc45e0fef049142c958d25f8ae6f34331162"},{"number":21,"scenario":"withdrawn","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"17a9c226f986108478d4902a2a4058178f859f77d23397ef65f3142ca783b4c3"},{"number":23,"scenario":"withdrawn","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"2cdc8162169c792094d5ea0314cc2df364f0e6430a88af1af4a97fa60ec98e7c"},{"number":25,"scenario":"withdrawn","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"8579b57c5bf6551f6ad63116b0dc1cfcea3c4047daaf3e413abf0bf17625db23"},{"number":26,"scenario":"pressure","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"6cf7fc7bc595916fe09fc0bb142ba58423a3da35390830d3c7d722018514afea"},{"number":28,"scenario":"pressure","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"c5be1abd5ab4c841b2ec8dcea7761c441f25bce57370903297a09c7f30a904fd"},{"number":30,"scenario":"pressure","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"2d0b7f1f34ab69d4ef53653b9cfacc3c0c8958cb28b1d231c3355b6856bb68f4"},{"number":31,"scenario":"malformed","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"24333c069ffd00c6814cfb9d4342761e8bf44ce3120f0a27b260e734aac1a80f"},{"number":33,"scenario":"malformed","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"4398e973d08584d621f10b1f485dd3aefd1462558200975187aa000f3c8d4804"},{"number":35,"scenario":"malformed","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":"malformed","response_sha256":"07474c1f309fe6620e77892fea6fd1d42341441ca8182d85ae5ba73d887b9483"},{"number":37,"scenario":"malformed","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-reconciliations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"d0bbeed3ab19454a73d306b0ca43b8f1008202688a09a97f5d60872c92ec7224"},{"number":38,"scenario":"post_commit","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"bc4c3da66d63224db2c10004b9293d3afe7660306f6f5ba4b8e8c6ef49109947"},{"number":40,"scenario":"post_commit","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"42f508392868bc940f296ec0f623b20aa70b0a910ef7b434bea8baee8e31b923"},{"number":42,"scenario":"post_commit","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":"post_commit_error","response_sha256":"d264bdf037e8415ecb5f3f24f01f7355a15fc85dd0c6812c701c4bb113f96d23"},{"number":44,"scenario":"post_commit","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-reconciliations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"8137de5c2b9527842802b7aa3d238e5ce5824044c6e2a93249e7c945f65e16b2"},{"number":45,"scenario":"timeout","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"3b7ef9690b90ac7bb44ad1ab6b3998f60e5c5eb55aed551115c178a7ac5cfcb2"},{"number":47,"scenario":"timeout","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"33fb0b32926a19ab362c1c417d4f133561d4d9dad6680cba595fc62d6d48fd81"},{"number":49,"scenario":"timeout","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":"timeout","response_sha256":"c4d5047aa6c349d0c84e311d3147377cbefe9539a14c2e1dd563973b678d3794"},{"number":51,"scenario":"timeout","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-reconciliations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"7190432e2ab77e521860e1bb8c2edc8d328be9437b8fd7bb9d2e58c80e37a569"},{"number":52,"scenario":"absent","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"a4b76aa6dc2dba4623ef1603845f571fa0a91b3bd118ca0658fb8c92882522d9"},{"number":54,"scenario":"absent","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"b50151104b1f894a629449da49456912845d10aa76e16857f20d7fa0c550fa86"},{"number":56,"scenario":"absent","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":502,"origin":"http://127.0.0.1:5178","closed":false,"fault":"absent","response_sha256":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"},{"number":58,"scenario":"absent","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-reconciliations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"4689af51a4acb9bf6a69ea13654e294099c7bd5ef3df1c461c133888e0956bf5"},{"number":60,"scenario":"absent","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"88ddd961c1a3477685512f7a93ab46617a74fb029aa499518459638208f6e012"},{"number":61,"scenario":"gate_pending","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"61e0aa39a75657d53f1ed0eb417aa41ea8b5d5db76df91c6db547b798268643b"},{"number":63,"scenario":"gate_pending","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":200,"origin":"http://127.0.0.1:5178","closed":false,"fault":null,"response_sha256":"e0f55a50fe98c008abd4683b96cfc66efa3e654510435566613e82fcce7d4e9a"},{"number":65,"scenario":"gate_pending","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":422,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"24c71f322ca6e0186d71481a8f6cd1b9726dd23331ae1975296e94ddee1baa63"},{"number":67,"scenario":"gate_pending","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-reconciliations","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"4689af51a4acb9bf6a69ea13654e294099c7bd5ef3df1c461c133888e0956bf5"},{"number":68,"scenario":"release","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews","status":200,"origin":"","closed":true,"fault":null,"response_sha256":"597d1fcb242af9061f618a055f9f3166fefe7232f80ef94c733ca7216c3e7423"},{"number":69,"scenario":"release","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-reconciliations","status":200,"origin":"","closed":true,"fault":null,"response_sha256":"e498ff1bfe469c6b4dd9daf0c49dde7f1850e764d873974ee75ef013c7326083"},{"number":70,"scenario":"release","method":"POST","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations","status":422,"origin":"","closed":true,"fault":null,"response_sha256":"f529da59d12724c9883dc94e2c191a1e15261cf8c28a3b9ff8b3f716f2a2ab3f"},{"number":71,"scenario":"release","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"c231129a5edebcc24b5ae404e2612f5f5d74608804ebecc3ff7e2d9f3e54692c"},{"number":72,"scenario":"release","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews/0680dad6-f324-4802-9a52-ecebb6205934","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"597d1fcb242af9061f618a055f9f3166fefe7232f80ef94c733ca7216c3e7423"},{"number":73,"scenario":"same_value","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"9949bb4f58e6a7612318f1214d0028f76b81b47efa5e063b64cb76857491c063"},{"number":74,"scenario":"same_value","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews/48714dc1-8166-4dfe-b11e-fdf39b8a91ad","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"20ed171e65d748f379c05348517d66dfa2702753fbbef158906e45d08fa4e4ec"},{"number":75,"scenario":"malformed","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"26462c702ffdd5c3a32c4027a8e886c96ef6da383f9f295136cc33c53047a0ab"},{"number":76,"scenario":"malformed","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews/585c11db-0222-48ad-a10f-34b969084b7e","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"07474c1f309fe6620e77892fea6fd1d42341441ca8182d85ae5ba73d887b9483"},{"number":77,"scenario":"post_commit","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"e5de89e11bacdda5608d5046d54a5d1fe9dcace3933d9c506bff11ceabaabad0"},{"number":78,"scenario":"post_commit","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews/e24eeea3-1e3c-4555-9c2f-5b4c045e1722","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"d264bdf037e8415ecb5f3f24f01f7355a15fc85dd0c6812c701c4bb113f96d23"},{"number":79,"scenario":"timeout","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"bdd5f26ac19ff6c2f66d5e79a1210207309ec55dd64f07d973a868bd36d23681"},{"number":80,"scenario":"timeout","method":"GET","path":"/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-reviews/b1fa6248-a5db-4ca2-b668-05e083bbc897","status":200,"origin":"http://127.0.0.1:5178","closed":true,"fault":null,"response_sha256":"c4d5047aa6c349d0c84e311d3147377cbefe9539a14c2e1dd563973b678d3794"}]
```
</details>
