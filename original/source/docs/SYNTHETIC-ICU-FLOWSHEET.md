# Read-only synthetic ICU flowsheet

Local downstream work after accepted descriptive explanation 33c729d. The separately unreviewed authored case-interpretation changes remain present. Director acceptance of 33c729d does not cover either new increment.

## Dataset and startup

`tools/run_comprehensive_demo.py --flowsheet --directory /absolute/new/path` explicitly creates a fresh disposable database. The original comprehensive default remains unchanged, with 41 current source items and optional HPI. The flowsheet option calls that baseline bootstrap first, preserving its two retained released/withheld examples, then appends 115 additional distinct source observations/events. The final real API view has 156 items and execution_enabled=false. No automatic production/startup seeding or configuration gate change is introduced. Existing databases are refused, not overwritten.

The fictional sequence includes four additional observation sets (08:15, 08:30, 08:45, 09:00 UTC) for MAP, CO, CI, CVP, HR, arterial pH/PaCO2/PaO2 and lactate. Each ABG set retains its own specimen and collection/respiratory context. The final CO is explicitly suspect-quality. Eleven vasoactive events show noradrenaline/norepinephrine, vasopressin and dobutamine orders, initiations, rate changes, pause, restart and stop. These are fictional charting examples, not a treatment protocol, dosing advice or evidence of response. Source dosing weight (70 kg), concentrations, route, pump/channel and separately recorded volumetric rates are provided for the new delivery events. Exact weight/pump references must match scope and revision; unavailable references stay missing rather than substituting a successor. Orders remain distinct from delivery. No dose/volumetric conversion is attempted.

Existing VasoactiveEvent, OrderEvent, InfusionEvent, InterruptionEvent and DeliveryDetails contracts are reused. Dobutamine is representable but is not admitted into the five-agent P/L/V vasopressor policy. Explicit source identifiers under clinrx.synthetic.infusion-series/v1 link the new fictional infusion instances, including interruption events; delivery details retain the same exact source infusion identity. A prior initiation without infusion identity is shown separately, not silently assigned to the new series.

## Display behavior

The new ICU flowsheet tab reads the already decoded bounded Patient State via the existing client. A scrollable table groups exact supported source timestamps in UTC, with separate rows for drug/infusion instances and measurement method/device/parameter/site/sample-type contexts. Multiple observations at one timestamp remain separate clickable sources. All source values and units retain spelling. Each source opens the existing inspector and signed-context history; the inspector now presents infusion event type, recorded/prescribed rate, concentration, route, weight gaps, pump/channel and infusion identity in readable form.

The time-axis placement is deliberately restrictive: in-window only, verified source clock, explicit precision declaration, known instant, matching whole-second UTC source and recorded timestamp spellings, and no conflicting/alternative times, recorded bounds/uncertainty or clock-alignment evidence. Fractional/offset/ambiguous/contextual/unplaced sources remain off-axis and inspectable with raw timestamps. This display does not broaden the protected timestamp policy or establish physiological simultaneity. Row sorting and grouping are presentation only, not clinical ranking or temporal inference.

No forward-filled dose segments, inferred administration intervals, interpolated lines, averaged CO, unit conversion, dose-equivalence calculation, treatment effect or response classification is produced. Blank cells mean no point observation/event at that time, not zero, continued delivery or stopping. Orders/preparations remain distinct from administration. Withdrawn/invalid/unknown/suspect source status is retained, not promoted. HPI remains optional; other families remain in the Evidence library.

The prior authored exact-case interpretation is correctly withheld for the expanded 156-item set because its exact-evidence guard no longer matches; no replacement clinical interpretation is automatically generated. The descriptive explanation and underlying recorded summary remain available.

## Safety and validation boundary

Production execution, clinical policy, inference/receipt semantics, dependencies and migrations remain unchanged. An optional `recorded_interval` field is added to CirculatoryEvent and the exported transport schema: source-asserted start/end ClinicalInstant boundaries plus provenance and limitations. None is omitted so pre-existing event canonical payloads remain unchanged. Boundaries retain the existing exact timestamp admission behavior; this field makes no duration or chronological-order assertion. Contradictory boundaries can be retained as source evidence, without a display-derived duration or rate. All new persisted data is disposable and synthetic. The existing gated browsing response is required; if execution_enabled is true or not safely decoded, the flowsheet is withheld with the rest of the workspace. No merge, deployment or publication is authorized by this local task.

Validation records separately identify focused backend/API tests, full frontend tests, typecheck, both local build modes, fixture export, live API/browser inspection and their limitations. New hosted CI/container or clinical acceptance is not inferred. Earlier accepted source/evidence references and database remain preserved.


## Hemodynamic coverage and module boundaries

| Priority | Added to this local synthetic chart | Boundary |
| --- | --- | --- |
| Integrated chart | One recorded UTC axis for BP/MAP/CVP, rhythm, CO/CI, infusion events, gases/lactate, perfusion and interventions; section filters and exact source inspectors. | No implied simultaneity, interpolation or forward-fill. Unknown/conflicting times remain off-axis. |
| Infusions | Noradrenaline, vasopressin and dobutamine order/start/change/pause/restart/stop examples; source units, concentrations, exact dosing weight and pump-rate support, route and infusion identity. | No prescribing, dose conversion, exposure estimation or pump control. Dobutamine does not enter the five-agent descriptive P/L/V policy. |
| Fluid context | Explicit interval urine, IV input, blood products, drains and CRRT NET removal; separately labeled source-calculated interval and cumulative totals. Explicit source zeros differ from missing cells. | No complete fluid reconciliation, calculated rates/balances, nutrition accounting or comprehensive renal treatment workflow. Intervention volume may already be included in charted input. |
| Measurement context | CO method, acquisition type, source averaging basis, calibration/zeroing status, respiratory phase, position and source BSA/indexing denominator. | No calculated average/BSA or automatic measurement-validity assessment. Raw provenance remains in the inspector. |
| Serial perfusion | Lactate/ABG, capillary refill, mottling, peripheral temperature and interval urine; separate ScvO2 and SvO2 specimens. | No shock diagnosis, perfusion score or interpretation of sedation/mental status. Mental status belongs to the relevant module and is not silently treated as normal. |
| Intervention review | Recorded fluid challenge, ventilation and fluid-removal context; exact baseline/intervention/subsequent references. | No fluid-response percentage, causal attribution or automated treatment recommendation. No successor substitution for missing originals. |
| Goals/handover | Clinician-recorded target, rationale/review time, review note and unresolved hemodynamic concerns. | These are source assertions, not an operational order-entry, escalation or patient-management workflow. |

Broader echo, RVSP, pulmonary-pressure findings and LVOT VTI remain available from the original evidence library and summary. HPI remains optional. This increment does not remove any evidence family. Nutrition, general patient management and comprehensive organ-system workflows remain owned by their other modules. VA-ECMO, Impella and IABP remain deferred.

## International documentation context

The comparison uses publicly available documentation patterns, not private hospital EHR access or adoption of one country's treatment policy:

- Canada, LHSC [cardiovascular monitoring documentation](https://www.lhsc.on.ca/critical-care-trauma-centre/standard-of-care-cardiovascular-monitoring) and [cardiac-output measurement procedure](https://www.lhsc.on.ca/critical-care-trauma-centre/procedure-cardiac-output-measurements).
- Australia, [Austin ICU referral form](https://www.austin.org.au/Assets/Files/Austin%20Intensive%20Care%20Unit%20Referral%20Form.pdf), a referral rather than hourly bedside chart.
- UK, [historical 2015 critical-care transfer chart](https://londonccn.nhs.uk/wp-content/uploads/critical-care_ncr-pages_2015-1.pdf), not a claim about current institutional policy.
- US, [MIMIC-IV archived ICU infusion structure](https://mimic.mit.edu/docs/iv/modules/icu/inputevents.html), a research representation of historical documentation, not a current EHR specification.

These examples informed separation of source times, fluid intervals, orders/delivery and measurement context. ClinRx does not claim worldwide policy completeness. Units and source clinician goals remain explicit, and no universal dose unit, target, recording frequency or freshness threshold is imposed.
