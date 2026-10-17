# Docker evidence wording erratum — initial echo capture

Documentation-only correction to the accepted captured-container evidence **392c43457c245924cc1844b2157dcbe67e813037**. Application remains **d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982**, tree **384bee3150f0428156549962da1147382f2f03f9**. The bounded captured-container acceptance stands. No application correction, repeat review, test run, recapture or Docker rebuild is requested.

## Corrected statement

**The initial screenshot visibly contains the expanded echo source caveat; its paired selected-inspector DOM omits that expanded text. Describe this as an initial screenshot/DOM inconsistency. Preserve both originals. The later keyboard screenshot and DOM agree and support the bounded acceptance. No application defect, cause for the initial mismatch, or pointer/touch reliability conclusion is established.**

This supersedes the inaccurate “both lack the expanded text/incomplete capture” description in:

1. [Reviewed START-HERE.md, section 4](https://github.com/shafin-lab/clinrx-ai/blob/392c43457c245924cc1844b2157dcbe67e813037/START-HERE.md) — [corrected reading copy](corrected/container-review-guide.md).
2. [Reviewed original/README.md, initial-disclosure paragraph](https://github.com/shafin-lab/clinrx-ai/blob/392c43457c245924cc1844b2157dcbe67e813037/original/README.md) — [corrected reading copy](corrected/container-validation-report.md).

The immutable reviewed documents retain the original wording as historical evidence. The reading copies fix the specified passages, retain historical attribution elsewhere, and point original artifact links back to the accepted evidence commit. The original PR handoff's description of that initial pair should be read with this correction.

## Preserved original evidence

| Capture | Correct description | Unchanged original |
|---|---|---|
| Initial JPEG | Expanded caveat is visibly present. | [container-echo-expanded.jpg](https://github.com/shafin-lab/clinrx-ai/blob/392c43457c245924cc1844b2157dcbe67e813037/original/container-echo-expanded.jpg) |
| Initial paired DOM | Expanded caveat is absent from the selected inspector. | [container-echo-expanded-dom.txt](https://github.com/shafin-lab/clinrx-ai/blob/392c43457c245924cc1844b2157dcbe67e813037/original/container-echo-expanded-dom.txt) |
| Later keyboard JPEG | Expanded caveat is present; later pair agrees. | [container-echo-keyboard-expanded.jpg](https://github.com/shafin-lab/clinrx-ai/blob/392c43457c245924cc1844b2157dcbe67e813037/original/container-echo-keyboard-expanded.jpg) |
| Later keyboard DOM | Expanded caveat is present in the selected inspector. | [container-echo-keyboard-expanded-dom.txt](https://github.com/shafin-lab/clinrx-ai/blob/392c43457c245924cc1844b2157dcbe67e813037/original/container-echo-keyboard-expanded-dom.txt) |

[PRESERVED-ARTIFACTS.json](PRESERVED-ARTIFACTS.json) records the four original lengths and SHA-256 identities checked against both the accepted original manifest and the original local capture directory. No original artifact, screenshot extension, reviewed manifest or lossless mirror was edited, replaced or relabelled. The original initial JPEG was also visually inspected to confirm the correction; DOM absence/presence was checked within the selected-inspector block, rather than across unrelated summary text.

## Boundaries

This corrects documentation, not the underlying application or accepted evidence. It does not revise Director's verdict, authenticate hidden image/signing-key bytes, establish a capture-race explanation, certify pointer/touch behavior or authorize hosting. No app/test/Docker rerun occurred for this correction. All prior stated limitations remain.

Only a new evidence erratum tag and a PR #23 comment are published. PR #23's application branch remains unchanged, draft/open/unmerged at 17e2064c3f1a1761876e9a42c5c7a131646d465c. Production connected execution remains disabled. No merge, deployment, external hosting or gate activation.
