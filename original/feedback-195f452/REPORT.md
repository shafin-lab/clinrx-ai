# RF2 feedback placement — local validation

Candidate195f4521002253d738685bf644564d51eb1acf4e, tree564789187c83b4250fa1fa502204b23d091375f4, parent8186bb72b6748372e229b8fe40548af14c90f238.

Two frontend/test files change. Validation, source-review, append and exact-recovery errors use one alert at the end of the draft section directly after its active controls. Source-history/reference errors retain their original source-area placement. Error messages are routed by feedback area; draft, pending command, source review decisions, handover state and all transport/recovery operations remain unchanged. No automatic focus jump, save, reset or retry was added.

41 focused tests/three files passed in3.78s with maxWorkers2, covering feedback locality, exact selections, source review and uncertain-save recovery/handover. Typecheck/default and explicit HOSTED/AUTHORING/RF1/RF2 builds passed. Existing bundle warning remains. The earlier754 full-suite result belongs to8186bb7; no full-suite rerun or exact-head CI is claimed for this bounded placement increment.

Installed locally with previous frontend preserved. Served HTML/JS/CSS equal tested build bytes. Backend process is unchanged and its source tree equals this candidate. All twelve database row exports remain unchanged:186 fact revisions, two retained receipts; SQLite integrity/foreign-key checks pass. Browser storage was not inspected or modified, and no browser reload was performed. No live-browser or broad accessibility acceptance is claimed. Existing browser access restriction remains respected.

No push, merge, deployment, external hosting or execution activation. Production execution remains disabled. Reload only after finishing or explicitly discarding a draft; pending commands require exact recovery before closure/reload.
