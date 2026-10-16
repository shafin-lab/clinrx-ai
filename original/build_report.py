from pathlib import Path
import json,hashlib,datetime
root=Path(__file__).resolve().parent
results=json.loads((root/'verified-results.json').read_text())
events=[json.loads(s) for s in (root/'events.jsonl').read_text().splitlines()]
body='''# ClinRx PR #23 — isolated browser-to-real-API validation

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
'''
descriptions={'release':'Released; browser retained lookup returned identical receipt','same_value':'Support-only same-value successor withheld; original CAL/1 retained, terminal CAL/2','provenance':'Provenance-only successor withheld; original CAL/1 retained, terminal CAL/2','withdrawn':'Withdrawn successor withheld; original CAL/1 retained, terminal withdrawn CAL/2','pressure':'Primary pressure successor withheld; original P/2 retained, terminal P/3','malformed':'Committed receipt with schema-valid foreign inference reference delivered to browser; completion unknown; explicit reconciliation recovered original receipt','post_commit':'Real API committed, then harness delivered HTTP 500; completion unknown; explicit reconciliation recovered receipt','timeout':'Real API committed; delivery delayed 35 seconds past actual 30-second client deadline; timeout then explicit reconciliation recovered receipt','absent':'First request intercepted before API dispatch, delivered 502; reconciliation absent; no receipt/no automatic retry; explicit same-command retry then released','gate_pending':'Prepared while isolated gate open; gate then closed; execution 422 and reconciliation absent; zero execution receipts'}
for case in results['cases']:body+=f"| {case['scenario']} | {descriptions[case['scenario']]} | `{case['execution_id']}` |\n"
body+='''
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

'''
body+='\n<details>\n<summary>Machine-checked receipt identities and results</summary>\n\n```json\n'+json.dumps(results,indent=2)+'\n```\n</details>\n'
body+='\n<details>\n<summary>Gate-closed storage proof</summary>\n\n```json\n'+(root/'gate-proof.json').read_text()+'\n```\n</details>\n'
transcript=[]
for e in events:
 if e['event']=='http' and e['method']!='OPTIONS':transcript.append({k:e[k] for k in ('number','scenario','method','path','status','origin','closed','fault','response_sha256')})
body+='\n<details>\n<summary>HTTP transcript (API status before any delivery fault)</summary>\n\n```json\n'+json.dumps(transcript,separators=(',',':'))+'\n```\n</details>\n'
(root/'README.md').write_text(body)
old=json.loads(Path('/tmp/clinrx-pr23-lifecycle-pr.json').read_text());assert old['headRefOid']==results['source_head']
append='\n\n---\n\n'+body
for name in ('harness.py','verify_evidence.py'):
 append+='\n<details>\n<summary>Isolated evidence script: '+name+'</summary>\n\n```python\n'+(root/name).read_text()+'\n```\n</details>\n'
prbody=old['body']+append
assert len(prbody.encode())<65000,len(prbody.encode())
Path('/tmp/clinrx-pr23-lifecycle-body.md').write_text(prbody)
(root/'checksums.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir()) if p.is_file() and p.name!='checksums.json'},indent=2)+'\n')
print('Local report written; PR description bytes:',len(prbody.encode()))
