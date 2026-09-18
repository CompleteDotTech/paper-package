# Concurrent integration and reporting clarification

The hypotheses were frozen against PR #17 (`a62a3257645d8e35cd4e45be53bfa9511d27724b`) before implementation. The first local execution and the first committed-source GitHub Actions run both returned H1/H3 target failures and H2/H4/H5 controlled target passes. `FIRST_OBSERVATION.json` preserves the original primary outcomes.

During execution, PR #18 (structural refinements) and PR #19 (source-risk and structural experiments) merged into main at `a21314d17c33c639b75522ecce120586ef8dab35`. This branch integrates that commit with genuine two-parent merge ancestry. All files from that main tree are retained, with only additive research files, combined manuscript-renderer markers, combined report-regeneration workflow steps and regenerated current-paper outputs changed. The preceding studies' own sources, results and manifests remain unchanged.

The new report now inserts after the source-structural section when present, otherwise after structural or reliability. Three reporting regression tests cover preserving other studies, idempotence and invalid anchors. The multicall regeneration chain includes every concurrent report before this report. The renderer strips all section markers. These are integration changes, not changes to hypotheses, algorithms, seeds, primary endpoints or target thresholds.

The H4 report additionally makes its cost-accounting boundary explicit: the cold reference executes value-only DP. The comparison charges it the same full-tree reconstruction traversal measured for the delta implementation. The combined count is an accounting model, not two separately timed reconstruction implementations or a wall-clock speedup. No benchmark numbers changed.

Global novelty remains unclaimed. The additions on main concern reliability ranking, diversification, alternative review models, bounded independent-event inference, conflict optimization and source revision invalidation. They are preserved as separate studies; the present five experiments retain their originally audited PR #17 baseline and limitations.
