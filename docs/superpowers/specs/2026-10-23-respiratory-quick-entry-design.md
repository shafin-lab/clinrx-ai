# Simpler respiratory findings entry

The user's requested layout is the implementation scope: common chest examination and imaging choices, editable free text, and source/method details under Advanced. Retain the existing React form, source owner, validation, review-before-save, retry identity and correction history.

Approach: add a small field-specific quick-choice control beside the existing editable value. No choice is preselected and no diagnosis or normal finding is generated. Choosing a value explicitly fills the editable wording; choosing Other focuses the existing value without clearing it. Imported custom wording and coding remain untouched unless that value is edited.

For bedside/imaging entry, keep information type, title, observation time, report text and findings prominent. Place source identifiers, source basis, report status and additional source/sample context under Advanced source details; each finding's type/quality/method goes under its own Advanced details. Show the recorded quality/basis and any comparator or unavailable state beside the value. Missing required source information opens Advanced with an actionable error. Keep the original ABG/mechanics control layout.

Alternatives: a new simplified storage format would fragment ownership; a second wizard would duplicate validation. Both are unnecessary for the user's explicit layout request. Use the existing source record throughout.

Constraints: all imaging optional; metadata alone is not a report. No source, patient database, migration, clinical threshold, treatment or execution-gate change. Original preview5238 and reviewed build063355 stay immutable while the new source is tested and reviewed.
