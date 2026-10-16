# Targeted bottom-of-chart scrolling evidence

Supplement to PR #23, addressing Director's missing lower-chart capture. No application changes or repeat full-suite run were needed. Production connected execution remains disabled. No merge, deployment or gate activation.

## Exact scope

Captured application source: [131f3413a664b05ad898518f3ce998715d08b53d](https://github.com/shafin-lab/clinrx-ai/tree/131f3413a664b05ad898518f3ce998715d08b53d), tree `a8f7012d7428de69aefa136d812ed8329b5a75c2`; working tree clean. This is the CURRENT eight-group ABG/echo descendant, not a fresh execution of the earlier six-group 6c10b00 head. [Source identity and relevant hashes](source-identity.json). The chart CSS is byte-identical to 6c10b00; descendant markup includes the disclosed ABG/echo additions. This supplement does not retroactively relabel the earlier lower.png or imply acceptance of pending ABG/echo code.

## Visual evidence

**[Bottom screenshot — fluid balance and perfusion with time headings](browser/bottom.png)**

[Starting top screenshot](browser/top.png), [before layout](browser/top-layout.json), [after layout](browser/bottom-layout.json), [complete bottom DOM](browser/bottom-dom.txt). All are fresh captures of the existing real local API-backed demo at http://127.0.0.1:5179/#demo-icu-time-chart. No fixture was replaced or backend gate changed.

## Recorded action sequence and observations

1. Combined overview selected, latest four source timestamps, all-times checkbox unchecked. Focus chart link used.
2. Focused the chart region and pressed Home. Captured top screenshot/layout with internal scrollTop 0.
3. Pressed End on that same region. In a subsequent tool call, captured screenshot and layout after scrolling settled. This separate observation avoids substituting a pre-scroll image.
4. Verified internal scrollTop 981.5, scrollHeight 1654, clientHeight 673: bottom reached within one-pixel rounding tolerance. Outer page scrollY remains 1229.5 before and after; chart bounding rectangle also remains unchanged. This establishes internal chart scrolling rather than only moving the page.

Observed viewport: 575 × 823; document width 575. Sticky headings remain at approximately y81–125. Fluid records occupy y358–648 and perfusion y648–754, inside the chart ending at y755. All nine fluid/perfusion source controls and four time headings are within the chart and viewport; the screenshot visually supports the layout measurements.

The screenshot shows 08:45, 08:50, 08:55 and 09:00 UTC on 8 October 2026. Visible records include source-reported cumulative +285 mL, interval +110/−50 mL, measured urine 40/45 mL with interval bounds, lactate 2.1/2.0 mmol/L, and capillary refill 2.0 seconds at both observation times. Missing quality and completeness qualifiers remain visible. These are synthetic source assertions, not calculated balances or treatment-response claims.

The complete DOM retains the execution-disabled banner. No execution buttons, gates, source data, application files or configuration were changed during this check. Browser is left at the bottom of the chart for user inspection.

## Verification and limits

[Portable data-only verifier](verify_evidence.py), [SHA-256 manifest](SHA256SUMS.json), [verification output](verification-output.txt). The verifier checks internal movement versus stationary page, viewport/container bounds, four sticky time headings, both groups and all nine controls fully inside the visible chart. It also checks the captured disabled-execution banner and displayed values/intervals. It does not perform browser actions or substitute for visual inspection of the screenshots.

Captured 17 October 2026, Asia/Kolkata. This is implementation-produced interaction evidence for this viewport, keyboard scrolling and source. It is not an independent Director live exercise, touch/pointer certification, universal accessibility claim, complete network trace, hosted preview or container validation. No fresh test-suite run or database commitment is claimed. Earlier evidence/acceptance boundaries remain unchanged.

[ABG/echo source and validation handoff](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6222803229); [six-group overview handoff](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6222653258). PR #23 remains draft/open at unchanged application head 17e2064.

Please inspect the bottom screenshot and layout evidence and state whether this closes the targeted bottom-of-chart interaction evidence gap for the current local demo. Do not infer wider shareable-hosting, clinical or gate approval. Keep production execution disabled; do not merge or deploy.
