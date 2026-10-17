# Packaged demo walkthrough

17 October 2026, Asia/Kolkata. Existing reviewed image from source 2539eb61292456706b3c358443a8fdb7a6ece144 restarted locally; no rebuild or source change. Bound only to http://127.0.0.1:5183. Kept running at the user’s request to inspect the packaged demo.

Story: packaged UI → same-origin read-only synthetic gateway → persisted 156-record ICU fixture → exact source inspector/history.

| Boundary | Evidence |
| --- | --- |
| Image/runtime | Inspected exact expected image ID and loopback-only binding; startup complete, no captured runtime error |
| API/data | Actual state returns 156 items, 14 populated families, execution_enabled=false; persisted rows match packaged fixture |
| Browser response | Packaged flowsheet shows 156 recorded items, 14/15 families, five flagged/unknown and two contextual/unplaced |
| Exact history | Opened fs-PH-60/1 and requested bounded history from the browser; one original retained revision displayed |
| Source timing | 09:00 ABG pH7.35, PaCO2 44mmHg, PaO2 88mmHg, sample FiO2 40%; 08:00 echo RVSP/PASP45mmHg, VTI17.5cm, EF55%, source-only caveats |
| Integrity | All 12 tables unchanged after the browser walkthrough; browser log API returned no entries |

New screenshots were saved with extensions detected from actual image bytes. Earlier reviewed evidence was not altered. No full suite, external hosting, deployment, merge or production gate activation. No live device connection, physiological inference or treatment advice. This walkthrough is implementation evidence, not Director review or general usability certification.
