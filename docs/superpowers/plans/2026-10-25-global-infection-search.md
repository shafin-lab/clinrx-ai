# Global infection search

User-requested design: move Find an infection above Clinical group and search the entire library regardless of the selected group. Keep grouped browsing for an empty query; show group names on search results and explicitly label results as spanning all groups. Clicking a result updates the browse-group selection; changing the group clears search, as before. Preserve NCDC, supplementary reference content, original preview and all patient stores.

Implementation: change only selection/filtering and navigation markup in `CompleteNcdcLibrary.tsx`; add `globalInfectionSearch.test.tsx`. No dependencies, API, source or database changes.

- [ ] Observe regression failures for cross-group names, multi-group context matches and control ordering.
- [ ] Implement global matching and group-labelled results, preserving context clearing.
- [ ] Run focused and full frontend tests, typecheck/build, desktop-browser search/group checks and preservation manifests.
- [ ] Publish at existing candidate origin5247 with prior build retained; leave original5246 unchanged.

Verification focus: no duplicates; accurate group count versus global-search count; case/whitespace normalization; no stale treatment/supplement after unmatched search; selecting a group clears global search. This is a small navigation correction implementing the user's explicit design, not a change to clinical guidance.
