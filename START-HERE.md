# ClinRx Director — synthetic hosting preparation review

Application source: [`28496c46494dcafc5440b92712eab382cd3c80de`](https://github.com/shafin-lab/clinrx-ai/tree/28496c46494dcafc5440b92712eab382cd3c80de)  
Application tree: `00aa087cce492bd94d4c36c1e0d4299d79fa7d89`  
Parent: Director-accepted preview-preparation baseline `8d3ce9cec1aa5c843cb25af385735d358fb02a44`  
[Hosting-only source comparison](https://github.com/shafin-lab/clinrx-ai/compare/8d3ce9cec1aa5c843cb25af385735d358fb02a44...28496c46494dcafc5440b92712eab382cd3c80de)

These files are published as a separate evidence tag, not changes to PR #23's
accepted application head. No ZIP or Mac task is needed to read them.
Nothing is merged, deployed or activated. Production execution stays disabled.

## Read first

- [Complete local validation report](README.md)
- [Source identity and changed-file hashes](source-identity.json), [commit bytes](source-commit.txt), [complete source diff](source.patch)
- [Hosting recipe and remaining release gates](source/docs/SYNTHETIC-DEMO-HOSTING.md)
- [Director's acceptance of the preceding demo baseline](director-baseline-review.txt)

## Validation records

- [Full backend: 4,243 passed](backend.log), [exact command/exit/timing](backend.json)
- [Full frontend: 443 passed](frontend.log), [exact Node 22.13.0/npm 10.9.2 command/exit/timing](frontend.json)
- [Typecheck](typecheck.log), [default build](build.log), [hosted build](hosted-build.log)
- [Real local HTTP exchanges](http-exchanges.json), corresponding raw `*-request.json`/`*-response.json` bodies
- [Restart evidence](restart-check.json), byte-identical retained receipt responses, stale-state-context rejection
- [Final browser evidence](final-browser), including [desktop](final-browser/desktop-overview.png),
  [390px source focus](final-browser/mobile-source-focus.png), [viewport/focus metadata](final-browser/mobile-source-focus.json),
  [keyboard focus return](final-browser/mobile-focus-return.txt), [empty console warning/error log](final-browser/console.json)
- [Original synthetic database snapshot](fixture-snapshot.sqlite3), [final synthetic database](hosted-synthetic.sqlite3),
  [all 12 tables before](rows-before-browser.json) and [after](rows-final.json)
- [Portable data-only verifier](verify_evidence.py)

All original local evidence bytes are preserved. [SHA256SUMS](SHA256SUMS) covers
the 99 original artifacts. [PUBLISHED-SHA256SUMS](PUBLISHED-SHA256SUMS) additionally
covers this entry guide and the original manifest. Root `browser-*` captures and
`node24-*` logs are earlier stages, explicitly distinguished from `final-browser/`
and the final Node 22.13.0 checks. No signing key or environment dump is published.

## Review boundary

Review the new same-origin, read-only client mode and the separate server gateway;
verify blocked preparation/execution/legacy routes, unchanged rows, retained results,
restart behavior, and Director's two UI follow-ups (source focus and authoritative
gate warning). Previous baseline approval is not acceptance of this new hosting code.

The Docker recipe is NOT container-validated: Docker was unavailable on this Mac.
No protected external HTTPS deployment, fresh-visitor access, provider selection,
cost or duration has been exercised or approved. A container build plus real hosted
access and usability checks remain release conditions. No hosted CI is claimed for
this increment. Do not infer clinical validation or approve production activation.

Review only. No merge, deployment or production gate activation is authorized.
