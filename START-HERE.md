# ClinRx Director — packaged patient-summary walkthrough

Evidence-only supplement linked from PR #23. No ZIP or Mac access required. No application changes, merge, deployment or external hosting. Production connected execution remains disabled.

## Exact source and image

Application: **2539eb61292456706b3c358443a8fdb7a6ece144**  
Tree: **d286b5c30bf01bcd0d2f6ab64df0a1d082a27a27**  
Image: **sha256:612977c31212cec5adcf9eb6fcd6dc8946808ac3998bd434aaadd4b7e696db0a**, Linux ARM64.  
Local page: **http://127.0.0.1:5183/#demo-icu-time-chart**, with Patient summary selected through in-page navigation. The hash need not change when selecting a demo view.

[Expected image metadata](reference-data/expected-image.json) is copied from the earlier walkthrough; [publication-time container inspection](publication-time-container-inspect.json) freshly confirms the same running image and binding only to 127.0.0.1:5183. This is not a new image build or source-file revalidation. The original browser observation took place on that packaged page, not Vite on 5179.

PR #23 remains draft/open at unchanged application head **17e2064c3f1a1761876e9a42c5c7a131646d465c**. Review tags do not move its application branch or establish exact-head hosted CI.

## Primary captured evidence

- **[Patient-summary explanation screenshot](original/explanation.jpg)**: original JPEG bytes with matching extension, showing the withheld case interpretation and “Patient-level relationship: not established” beside the explanation.
- **[Complete original patient-summary DOM](original/current-dom.txt)**: 156-record coverage; three evidence-stream explanations; 98 detailed summary-source controls; 13 record-specific uncertainty controls; source values, raw units, times, placement, quality/status and sample/study context.
- [Original capture checksums](original/SHA256SUMS.json) record the two unchanged copied artifacts. The originals in the local walkthrough directory and all earlier reviewed evidence remain untouched.

The screenshot is one viewport, not a full-page screenshot or proof that every stream/control is simultaneously visible. Complete DOM is supplied to inspect the content beyond that viewport. No full action/console/network trace was saved for this summary walkthrough. A suspect CO source was opened during the observed walkthrough, but its inspector DOM was not saved as a separate artifact; do not reconstruct a raw request or claim every control was clicked.

## What the summary actually establishes

The page groups blood-sample, flow/pressure and echo records for browsing. It links the following complementary source contributions without generating a combined diagnosis:

- **Blood gases:** 22 records in the stream. Sample type, collection time and each source's own respiratory settings remain explicit; absent venous settings are not substituted. Bicarbonate/base-excess source calculations retain caveats.
- **Flow and pressures:** 34 records in the stream, including nine CO records with distinct methods/times/placement. No preferred CO, equivalence, average, trend, oxygen-delivery calculation or shock subtype is inferred.
- **Echo:** 12 records, including ventricular/valve/pericardial findings, LVOT VTI and RVSP/PASP source estimates. The 08:00 echo remains separate from later ABG/flow records. VTI is not used to calculate CO; PH/PAH is not confirmed.

At 09:00 the displayed arterial ABG is pH7.35, PaCO2 44mmHg and PaO2 88mmHg with sample FiO2 40%; the CO4.60L/min retains suspect quality. Earlier echo examples include RVSP/PASP45mmHg, VTI17.5cm and EF55%. These are source values, not new calculations or clinically interpreted combinations.

**Important boundary:** “Patient-level relationship: not established” remains explicit. The authored patient-specific possibilities are **unavailable/withheld** because the current patient/window/evidence differs from the original authored case. Nothing is automatically regenerated. This is expected exact-case guard behavior, not evidence that this expanded case received a clinical interpretation.

Uncertainty remains visible: unknown PiCCO quality; suspect fs-CO-60 with its source caveat; contextual earlier CO; unplaced pressure; absent venous-sample settings; source-calculated echo limitations. Source quality is not promoted into confidence in a combined explanation. The summary's perfusion/support section is additional source context, not proof of treatment effect. Optional HPI is absent.

## Reused reference data — not a fresh capture

[Reference API response](reference-data/state-response.json) is copied byte-for-byte from the earlier packaged walkthrough evidence, **d8845cda478647e93e1fb1f426fd6c9be9321827/original/state-response.json**. It is not a new API request or database export made during this summary walkthrough. Its 156-item payload/digest/assembly identity can be independently recomputed.

[Earlier readable API items](https://github.com/shafin-lab/clinrx-ai/blob/d8845cda478647e93e1fb1f426fd6c9be9321827/readable-state/items-index.json) and [table exports](https://github.com/shafin-lab/clinrx-ai/blob/d8845cda478647e93e1fb1f426fd6c9be9321827/readable-tables/index.json) remain available. Earlier before/after-table equality belongs to that separate walkthrough and its publication-time history supplement; **no new all-table comparison is claimed for this summary navigation**.

[Lossless text-mirror index](text-mirrors/index.json) exposes the larger screenshot, DOM and reference-state bytes in ordered small base64 chunks with exact lengths and hashes. No ZIP or inaccessible binary is required. The raw reference retains its synthetic bounded read-context value; no signing key, real patient data or provider/account credentials are included. Checksum correspondence does not authenticate the context signature.

## Prior evidence relationship

- [Packaging/56-test/ARM64 handoff](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6229626772).
- [Packaged ICU flowsheet walkthrough](https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6229737831).

Preserve prior accepted frontend behavior. Independent packaging/walkthrough acceptance is not assumed. No tests, backend suite, hosted CI, new build, container restart, database export or clinical review were run for this evidence-only summary publication. The existing local container remains running at the user's request; this is not external hosting.

## Review request and limitations

Please inspect the actual screenshot and DOM and independently verify source-control/reference correspondence, explicit withheld interpretation, stream separation, source times/context and uncertainty disclosures. [Portable data-only verifier](verify_evidence.py), [publication manifest](SHA256SUMS.json), [implementation verification output](verification-output.json) support independent recomputation but are not Director acceptance.

Return a bounded verdict on the captured packaged-summary claims and identify any specific unsupported claim or missing artifact. This is implementer-captured evidence, not a live session witnessed by Director, an every-control or all-viewport/touch/accessibility test, fresh-visitor authentication test, complete network trace, clinical validation or hosting acceptance.

Keep production connected execution disabled. Do not modify the repository, merge, deploy, host externally or activate gates.
