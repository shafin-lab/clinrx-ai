# Patient-specific synthetic case interpretation

Local work after 33c729d. This expands clinical meaning beyond the descriptive explanation currently under review; prior acceptance does not cover this increment. Production execution remains disabled. No merge, deployment or publication is part of this local task.

## Presentation

The new Patient summary section is authored for synthetic-p1 / synthetic-e1, in the original 8 October 2026 08:00–10:00 UTC view. It presents three distinct levels: recorded source assertions; unconfirmed possibilities; and what prevents confirmation. “Confirmed” explicitly refers only to presence of source records, not physiological accuracy or confirmed diagnoses.

Possible respiratory contribution to acidemia / an oxygenation concern and possible increased RV pressure loading are discussed together, without establishing a common episode, causal mechanism, low-output state, shock, PH/PAH diagnosis or treatment. Cardiac output, cardiac index, LVOT VTI and EF are retained as separate observations; their presence does not prove adequate flow, oxygen delivery or perfusion. Unknown-quality PiCCO is not used as corroborating proof. Full source inspection remains available.

## Exact case guard

syntheticCasePins.json is a new, explicit authoring snapshot, generated from the already accepted 41-record synthetic fixture. It is not imported from test code at runtime. All facts, expected digests, inclusion, contextual references and view disclosures are compared by stable key-sorted structural serialization. Nested array order and exact string spelling are retained. No value coercion, physiological calculation, temporal comparison or general clinical threshold rule is introduced.

Patient/encounter and either of the two existing exact UTC spellings of the authored window must match. Every supplied record must belong to that scope. The complete non-HPI source set must match, with no missing, additional or duplicate identities. Source corrections, same-value provenance changes, withdrawal, quality/context changes or changed disclosures withhold the entire authored narrative. It is removed immediately on rerender, with an explanation; it is not automatically regenerated or relabeled for another patient. Current source browsing remains available. HPI is optional and explicitly unconsumed; same-scope HPI presence does not unlock or alter the interpretation.

This comparison is a display safeguard, not clinical eligibility, source authentication or a substitute for transport decoding. Normal decoded state and the existing execution-disabled browsing gate remain required. It cannot establish completeness beyond the loaded bounded state, detect future changes before refresh or authenticate records independently.

## Clinical background and limits

- ATS, Interpretation of Arterial Blood Gases: https://www.thoracic.org/professionals/clinical-resources/critical-care/clinical-education/abgs.php — pH/PaCO2 pattern and need to assess compensation/mixed processes. No formula or general threshold engine is implemented.
- ASE 2025 right-heart/PH guideline: https://www.asecho.org/guideline/right-heart-in-adults-pulmonary-hypertension/ — multiparameter right-heart assessment, pressure-estimate limitations, septal configuration and distinction from invasive PH characterization.

These sources informed the authored clinical possibilities; they do not validate this application or synthetic interpretation. No confidence percentage, certainty grade, new clinical-policy approval, new receipt, protected execution or LLM/API call is introduced. No backend, transport, fixture, policy, production-configuration, dependency or migration file is changed. Independent Director review of this new layer remains pending.
