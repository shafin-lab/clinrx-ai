# ClinRx Director — 156-record patient-summary walkthrough supplement

**Application d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982** · tree **384bee3150f0428156549962da1147382f2f03f9**. This evidence-only supplement belongs with the [authored-explanation code and validation handoff on PR #23](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6229921744). It introduces no code change. No ZIP or Mac access is required.

Production connected execution remains disabled. No merge, deployment, external hosting or gate activation. PR #23 remains draft/open/unmerged at 17e2064c3f1a1761876e9a42c5c7a131646d465c; review tags do not move its branch. Director review of the new authored explanation is pending; earlier Docker acceptance does not cover it.

## The three actual captures from this walkthrough

1. [Patient-summary screenshot](original/patient-summary.jpg): actual JPEG bytes with matching extension. It shows the explicitly authored 156-record profile and combined unconfirmed possibilities. This is one narrow viewport, not proof of every panel simultaneously visible.
2. [Complete patient-summary DOM](original/patient-summary-dom.txt): 156-record coverage, HPI optional, execution disabled, four authored panels, 42 exact case-source controls, the retained 98 summary controls/13 uncertainty controls, source times/sample contexts and limitations.
3. [Selected noradrenaline inspector DOM](original/noradrenaline-inspector-dom.txt): fs-N-CHANGE/1 at 08:15; 7 mcg/min; 0.08 mg/mL; actual dosing weight 70 kg linked to fs-WEIGHT/1; separately recorded pump rate 5.25 mL/h linked to fs-PUMP-RATE-N-CHANGE/1; route, pump/channel/infusion identities and unresolved raw-unit mapping. No conversion, continuous exposure or treatment effect is inferred. This supplement has no separately saved screenshot of this inspector; inspect its captured DOM.

[Original capture checksums](original/SHA256SUMS.json) preserve these three files without changes. Earlier reviewed artifacts are untouched. [Capture correspondence](capture-correspondence.json) explicitly records that the newly saved summary DOM is byte-identical to the earlier summary DOM; it is not a claim of new application behavior or fresh API state.

## What was walked through

The implementer inspected the already loaded local static-build summary at **http://127.0.0.1:5179/**, not the accepted packaged image on 5183. The UI confirmed 156 records, 14/15 families and new execution disabled. HPI was absent/optional.

- **ABG:** recorded arterial pH/PaCO2 7.30/50 mmHg at 08:15 and 7.35/44 mmHg at 09:00. The later source was opened and showed its own specimen, 40% FiO2 and PEEP 5 cmH2O. The authored text permits a possible changing respiratory contribution but does not confirm the cause or resolution.
- **Flow:** the opened 09:00 CO was 4.60 L/min with suspect quality; the earlier PiCCO value retained unknown quality. The explanation leaves flow adequacy, low output/shock and a preferred measurement unresolved.
- **Echo:** the source controls retain the earlier 08:00 RVSP/PASP 45 mmHg estimates and LVOT VTI 17.5 cm. RVSP's estimate-basis disclosure was expanded during the walkthrough: source TR velocity/estimated RAP, no ClinRx recalculation, undocumented RVOT obstruction context. The authored possibility of RV pressure loading does not confirm PH/PAH, acute RV failure or applicability to the later gases/flow.
- **Infusions/perfusion:** documented noradrenaline change, dobutamine pause/restart and vasopressin stop appear alongside MAP 61 then 70 mmHg, lactate 2.4 then 2.0 mmol/L, refill 3 then 2 seconds and urine volumes over explicit intervals. Their sequence does not establish drug effect or improved perfusion. The noradrenaline inspector's exact captured details are linked above.

The ABG, CO and RVSP inspections were observed by the implementer during this walkthrough, but no separate new inspector DOM/screenshots or full action/network trace were saved for those visits. Do not reconstruct missing captures or claim these three newly saved files prove every click. Earlier same-source [ABG inspector](https://github.com/shafin-lab/clinrx-ai/blob/40449e570823e70102741f4290960ae4c95be8de/original/serial-ph-inspector-dom.txt), [CO inspector](https://github.com/shafin-lab/clinrx-ai/blob/40449e570823e70102741f4290960ae4c95be8de/original/suspect-co-inspector-dom.txt) and [RVSP inspector](https://github.com/shafin-lab/clinrx-ai/blob/40449e570823e70102741f4290960ae4c95be8de/original/rvsp-inspector-dom.txt) remain separate evidence from the previous validation. Their collapsed nested sections do not prove expanded visual contents in that earlier capture.

## Reference data and verification

[Reused API content](reference-data/fresh-state-content.json) and [provenance](reference-data/provenance.json) identify byte-for-byte copies from earlier evidence **40449e570823e70102741f4290960ae4c95be8de**. “Fresh” is part of the prior filename and refers to the original validation, not this walkthrough/publication. No new API response, database snapshot, signed-context authentication or network trace is claimed. [Individually readable 156 items](https://github.com/shafin-lab/clinrx-ai/blob/40449e570823e70102741f4290960ae4c95be8de/readable-state/items-index.json) and [prior table exports](https://github.com/shafin-lab/clinrx-ai/blob/40449e570823e70102741f4290960ae4c95be8de/readable-tables/index.json) remain accessible.

[Lossless text-mirror index](text-mirrors/index.json) exposes the screenshot, both DOMs and large reference content in small ordered base64 chunks with exact length/hash metadata. [Publication checksums](SHA256SUMS.json), [data-only verifier](verify_evidence.py) and [implementation verification output](verification-output.json) support independent recomputation. No signing key or provider credential is included.

The verifier checks 156 fact digests and assembly identity, all 42 case-source controls, all 98 summary controls and 13 uncertainty-control references against reused data; it checks exact noradrenaline identity, delivered quantities, dosing-weight/pump support and captured restrictions. It verifies JPEG format/extension and lossless mirrors. This is captured-content correspondence, not cryptographic authentication of a live browser's data provenance, clinical endorsement or proof that all controls were clicked.

The existing **547-test** result, typecheck/default/hosted-mode builds and seven tested-source hashes belong to the prior application validation. No app/test/backend rerun, new container validation, exact-head hosted CI, fresh API/database export, live independent review, all-viewport/pointer/accessibility certification or clinical validation was performed for this supplement. Original incomplete Vite attempts and unexplained older parallel-run timeout uncertainty retain their prior disclosures. No duplicate full-suite run is requested solely for this evidence publication.

## Requested review

Use this supplement together with the original authored-explanation handoff. Inspect actual pixels/DOM and independently recompute the relevant correspondence. Review recorded findings versus unconfirmed possibilities, exact source times, sample/method/quality context, retained source callbacks, the expanded full-set guard, separately labelled original 41-record profile and optional-HPI collision safety. Preserve the distinction between patient-level relationship “not established” and separately authored possibilities.

Return a bounded verdict with exact source/evidence identities, required corrections, nonblocking findings and limitations. State what you inspected or reran. Do not extend earlier Docker acceptance or claim clinical readiness. Keep production execution disabled; do not modify, merge, deploy, host externally or activate gates.
