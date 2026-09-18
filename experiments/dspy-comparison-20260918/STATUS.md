# DSPy / Jev comparison: actual execution status

**Live with/without-DSPy comparison: NOT COMPLETED. No new Jev inference calls and no new DSPy inference runs were completed.**

## Live execution blockers

[Preflight run 35355158096](https://github.com/CompleteDotTech/paper-package/actions/runs/35355158096) found the mapped TypeSafe key populated, but none of `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`. It stopped before calling Jev. This does not establish whether differently named or environment-scoped provider credentials exist, or whether the TypeSafe key is valid.

[Diagnostic run 35355491970](https://github.com/CompleteDotTech/paper-package/actions/runs/35355491970) was marked `action_required` with zero jobs. Its gate was left intact. Broad secret-context diagnostics were removed; preflight and live runs are manual-only and use explicitly named keys. Secret values are not in these reports.

## Executed offline checks

**1,092 tests passed; 6 skipped; 16 test suites completed. All 11 deterministic experiment replays passed.** The original 161-file inventory and the existing optimizer inventory also passed verification.

Four SDK contract tests were skipped because SDK packages were not installed in this local runtime; two archived reproduction tests also reported skips. Skips are not counted as passes. An initial reproduction invocation lacked PYTHONPATH; the corrected invocation passed. A later combined wrapper timed out on two replay processes; the individual replay commands recorded below had already passed. Neither failed attempt is treated as an additional successful test.

| Check | Tests discovered | Skipped | Result |
|---|---:|---:|---|
| replay-adaptive | 0 | 0 | passed |
| replay-assumption_aware | 0 | 0 | passed |
| replay-followup | 0 | 0 | passed |
| replay-frontier | 0 | 0 | passed |
| replay-novel_mechanisms | 0 | 0 | passed |
| replay-reliability | 0 | 0 | passed |
| replay-risk_control | 0 | 0 | passed |
| replay-source_structural | 0 | 0 | passed |
| replay-structural | 0 | 0 | passed |
| replay-theory_suite | 0 | 0 | passed |
| replay-uncertainty | 0 | 0 | passed |
| test-graph_synthesis-adaptive-tests | 64 | 0 | passed |
| test-graph_synthesis-assumption_aware-tests | 47 | 0 | passed |
| test-graph_synthesis-corpus-tests | 32 | 0 | passed |
| test-graph_synthesis-dspy_benchmark-tests | 26 | 0 | passed |
| test-graph_synthesis-dspy_jev_optimizer-tests | 35 | 4 | passed |
| test-graph_synthesis-followup-tests | 67 | 0 | passed |
| test-graph_synthesis-frontier-tests | 75 | 0 | passed |
| test-graph_synthesis-novel_mechanisms-tests | 92 | 0 | passed |
| test-graph_synthesis-reliability-tests | 63 | 0 | passed |
| test-graph_synthesis-risk_control-tests | 66 | 0 | passed |
| test-graph_synthesis-source_structural-tests | 86 | 0 | passed |
| test-graph_synthesis-structural-tests | 36 | 0 | passed |
| test-graph_synthesis-tests | 200 | 0 | passed |
| test-graph_synthesis-theory_suite-tests | 37 | 0 | passed |
| test-graph_synthesis-uncertainty-tests | 36 | 0 | passed |
| test-reproduction-tests | 136 | 2 | passed |
| verify-frozen | 0 | 0 | passed |
| verify-optimizer | 0 | 0 | passed |

The machine-readable [validation record](offline-validation-summary.json) includes per-suite status and counts; the downloadable audit bundle also includes commands, durations and log hashes. These runs disabled socket connections and used no inference keys. They reproduce saved observations and algorithm fixtures, not newly optimized model predictions.

## Separate archived calibration analysis

[Archived calibration results](archive-calibration/RESULTS.md) refit fixed calibrators on the original calibration split and score saved test responses. They contain zero fresh inference and zero DSPy runs. Invalid archived response exclusions and denominators are explicit. Do not attribute these results to DSPy.

## Ready-to-run live comparison

[Protocol and commands](../../graph_synthesis/dspy_benchmark/README.md) cover five repeats, two DSPy search objectives, eight original native formulations, seven calibration settings and seven task/panel combinations. The code was tested with controlled doubles, not substituted for live inference.

To execute live, map an authorized generative-provider credential and model into the workflow, resolve the repository Actions approval requirement, and manually run the live workflow. Original manuscripts, predictions and the immutable root manifest remain unchanged.
