# Local source-linked patient-summary explanation

New frontend-only work after the independently accepted summary source a9e72c5.
That review does not cover this increment. No backend/model, transport schema,
fixture, dependency, migration, execution policy or production configuration is
changed. No merge, deployment, push or execution-gate activation is authorized.

The summary now explains three complementary streams: recorded blood/oxygen
context; recorded flow/pressures; and echo structure/function/estimates. Explanatory
text is fixed and inspectable. Case-dependent content is limited to the validated
records, source links, availability counts, source flags and source caveats.
There is no LLM/API call, clinical threshold, numerical coercion, time comparison,
preferred value, averaging, acid-base diagnosis, integrated score, oxygen-delivery
calculation, PH/PAH classification, causal conclusion or treatment recommendation.
The patient-level relationship remains explicitly not established.

Each stream links all its recorded sources through the existing inspector and
cutoff-bounded history. Multiple CO methods and contextual records stay separate.
Source-specific uncertainty retains quality/status, unavailable results,
contextual/unplaced inclusion, missing oxygen sample fields, source-calculated echo
estimates, source disclosures and acquisition/quality limitations/artifacts.
Missing respiratory fields are not treated as proof of clinical ineligibility;
applicability is explicitly not assessed. These are limited display checks, not a
complete quality or eligibility assessment. Recorded acceptable quality is not
confidence in a combined interpretation. Raw units are not normalized and
calibration applicability is not resolved here. No freshness threshold is added.

View-level disclosures are deduplicated by exact text, separately from source
quality/estimate flags, while retaining all associated source items and inspector
links. No caveat is dropped. Missing streams show an explicit absence of records,
not a clinical conclusion. Source estimate basis and incomplete RVOT-obstruction
documentation remain visible. All original summary records remain below.

The prior review's nonblocking test-fixture cleanup is included: the RVSP summary
history test now builds matching RVSP revision 1 from the actual expanded state,
validates its response through decodeCirculatoryHistory with the expected source
reference and scope, and asserts the returned history identity. It no longer uses
a different source's two revisions to stand in for RVSP history.

Validation covers source-specific uncertainty, withdrawn/invalid/suspect evidence,
empty streams, repeated view caveats, no invented overall confidence, exact source
inspection and gate-closed rendering. New browser captures and frontend checks
are retained separately from the previously accepted source/evidence. No duplicate
backend run or fresh hosted CI/container acceptance is claimed for this increment.

General explanatory context was checked against primary guidance without importing
clinical thresholds or claiming guideline/clinical validation:

- [AARC blood-gas analysis and hemoximetry guidance](https://www.aarc.org/wp-content/uploads/2025/03/davis-et-al-2013-aarc-clinical-practice-guideline-blood-gas-analysis-and-hemoximetry-2013.pdf)
- [ASE right-heart and pulmonary-hypertension guidance](https://www.asecho.org/guideline/right-heart-in-adults-pulmonary-hypertension/)
