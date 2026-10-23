# Local synthetic ABG and broader echo expansion

This local expansion follows hosting-preparation checkpoint `28496c4`. It is new
work requiring its own review; previous Director acceptance is not approval of
these changes. No production configuration, execution policy, migration,
dependency, merge, push or deployment is part of this change.

## Source evidence

The default disposable case contains 41 records in 14 of the 15 supported M7
families. HPI is absent by default and is explicitly optional. The existing
Acumen source prediction can be included with the Python bootstrap's
`include_hpi=True` argument; that produces 42 records and all 15 families without
changing the execution gate or the retained P/L/V examples.

Seven arterial blood-gas/haemoglobin source records retain pH 7.31, PaCO2 48.0
mmHg, PaO2 78.0 mmHg, bicarbonate 23.0 mmol/L, base excess -2.0 mmol/L,
measured saturation 95.0%, and haemoglobin 10.2 g/dL. These are fabricated display
examples, not reference ranges or treatment targets. Bicarbonate and base excess
are labelled as source analyzer calculations, not ClinRx calculations. Lactate
remains a separate recorded result and is not claimed to be part of this sample.

ABG context retains the arterial specimen identity and collection assertion,
source FiO2 40%, volume assist-control ventilation, PEEP 5 cmH2O and provenance.
These are sample-time settings, not assumed current settings. Context absent
from another record remains absent; it is never copied from the ABG panel.

Echo now includes LVOT VTI, EF, estimated RVSP and PASP, TR peak velocity, RV
basal dimension and function, septal configuration, valve findings, pericardial
findings and a source-reported pulmonary-hypertension impression, alongside
TAPSE. All are recorded source assertions linked to the synthetic study/report.
RVSP/PASP estimates remain distinct from invasive PAC/RHC measurements. Their
source estimate basis and incomplete RVOT-obstruction documentation remain
visible; no equivalence is inferred, and ClinRx does not calculate either value.
No PH diagnosis, PAH subtype, probability category or treatment is inferred.

## Contract and compatibility boundary

The 15-family registry is unchanged. Four additive concepts (`ph`, `paco2`,
`bicarbonate`, `base_excess`) extend the existing `circulatory_oxygen` family,
whose display label now includes blood gases. Optional typed `BloodGasContext`
retains collection/respiratory context and provenance. The field is omitted from
serialization when absent, preserving canonical historical oxygen payloads.
Source quantities continue using exact decimal strings and raw units without
conversion. New PaCO2 assertions require arterial or unknown sample type;
noninvasive records cannot claim sampled blood-gas context. Existing PaO2
admission semantics are unchanged.

These changes do not extend P/L/V eligibility or consume ABG/echo for new
inference. Source display and inspection remain read-only, and the API must
report execution disabled before this workspace will browse evidence.

## Local verification

Run the full backend suite, frontend suite, typecheck and both default and hosted
build modes. Focused tests cover actual API/persistence round trips, omitted HPI,
optional included HPI, retained release/withhold, gate rejection, unchanged rows
under gateway reads, exact quantities, sample correspondence, missing context,
source-estimate boundaries and historical oxygen serialization compatibility.

`tools/export_comprehensive_fixture.py` generates the expanded frontend test
state through the real API in a fresh disposable database. Its state-context
value is replaced with an opaque, nonfunctional fixture placeholder.

The normal runner still uses a fresh database on loopback only. Earlier demo
captures/databases are not modified. The local validation report records commands,
exit codes, runtime versions, source file hashes, browser captures and live API
checks. No hosted CI or new Linux container validation is claimed for this local
expansion.

## Clinical source context

Field selection was checked against primary sources, without importing their
clinical thresholds into the application:

- [ASE 2025 right-heart and pulmonary-hypertension guidance](https://www.asecho.org/guideline/right-heart-in-adults-pulmonary-hypertension/)
- [AARC blood-gas analysis and hemoximetry guidance](https://www.aarc.org/wp-content/uploads/2025/03/davis-et-al-2013-aarc-clinical-practice-guideline-blood-gas-analysis-and-hemoximetry-2013.pdf)
